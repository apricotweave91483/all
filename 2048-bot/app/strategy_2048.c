/*
 * 2048 expectimax strategy — standalone C.
 * Reads 4x4 grid from stdin (4 lines, 4 space-separated ints: 0,2,4,8,...).
 * Writes best move to stdout: "up\n", "down\n", "left\n", or "right\n".
 *
 * Build: gcc -O3 -march=native -o strategy_2048 strategy_2048.c -lm -lpthread
 * Args:  [depth_low] [depth_high] [serious_empty] [serious_max_tile] [max_empty_samples] [search_timeout_sec]
 * Defaults: 4 9 5 512 10 0  (timeout>0 => iterative deepening within that many seconds)
 *
 * Further performance ideas: -O3 -march=native; larger CACHE_SIZE; move ordering at max nodes;
 * parallel chance nodes (harder); iterative deepening (done when timeout>0).
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <pthread.h>
#include <time.h>

#define N 4
#define CACHE_SIZE (1 << 23)  /* 8M entries per thread */
#define MAX_EMPTY_SAMPLES 10
#define GAMMA 0.95
#define NTHREADS 4

typedef int grid_t[N][N];

typedef struct {
    unsigned long long key_lo;
    unsigned long long key_hi;
    double value;
    int used;
} cache_entry_t;

/* Per-thread cache; each root worker uses its own. */
static __thread cache_entry_t *current_cache = NULL;
static cache_entry_t *caches[NTHREADS];
static int depth_low = 4, depth_high = 9, serious_empty = 5, serious_max_tile = 512;
static int max_empty_samples = MAX_EMPTY_SAMPLES;

static void grid_copy(grid_t dst, const grid_t src) {
    for (int r = 0; r < N; r++)
        for (int c = 0; c < N; c++)
            dst[r][c] = src[r][c];
}

/* Rotate 90° clockwise */
static void rotate_cw(grid_t g) {
    grid_t t;
    for (int r = 0; r < N; r++)
        for (int c = 0; c < N; c++)
            t[c][N - 1 - r] = g[r][c];
    grid_copy(g, t);
}

/* Move row left: merge equal adjacent, shift. Returns score gained and whether changed. */
static int move_row_left(int row[N], int *score_out) {
    int out[N], n = 0, score = 0, i = 0;
    while (i < N) {
        if (row[i] == 0) { i++; continue; }
        int v = row[i];
        if (i + 1 < N && row[i + 1] == v) {
            out[n++] = v * 2;
            score += v * 2;
            i += 2;
        } else {
            out[n++] = v;
            i++;
        }
    }
    int changed = 0;
    for (int j = 0; j < N; j++) {
        int val = j < n ? out[j] : 0;
        if (row[j] != val) changed = 1;
        row[j] = val;
    }
    *score_out = score;
    return changed;
}

/* Apply "left" to grid; return total score and whether any change */
static int move_left(grid_t g, int *score_out) {
    int total = 0, any = 0;
    for (int r = 0; r < N; r++) {
        int sc;
        any |= move_row_left(g[r], &sc);
        total += sc;
    }
    *score_out = total;
    return any;
}

/* direction: 0=up, 1=right, 2=down, 3=left. Rotations match Python (rotate 90 cw = zip(*[::-1])). */
static const int rot_before[] = { 3, 2, 1, 0 }, rot_after[] = { 1, 2, 3, 0 };
static int do_move(grid_t g, int dir, int *score_out) {
    grid_t cpy;
    grid_copy(cpy, g);
    for (int k = 0; k < rot_before[dir]; k++)
        rotate_cw(cpy);
    int ch = move_left(cpy, score_out);
    for (int k = 0; k < rot_after[dir]; k++)
        rotate_cw(cpy);
    grid_copy(g, cpy);
    return ch;
}

static int count_empty(const grid_t g) {
    int n = 0;
    for (int r = 0; r < N; r++)
        for (int c = 0; c < N; c++)
            if (g[r][c] == 0) n++;
    return n;
}

static int max_tile(const grid_t g) {
    int m = 0;
    for (int r = 0; r < N; r++)
        for (int c = 0; c < N; c++)
            if (g[r][c] > m) m = g[r][c];
    return m;
}

static int corner_score(const grid_t g) {
    int m = max_tile(g);
    if (g[0][0] == m || g[0][N-1] == m || g[N-1][0] == m || g[N-1][N-1] == m)
        return 1000;
    return 0;
}

static int line_mono(const int *line) {
    int vals[N], n = 0;
    for (int i = 0; i < N; i++)
        if (line[i] != 0) vals[n++] = line[i];
    if (n <= 1) return 0;
    int inc = 1, dec = 1;
    for (int i = 0; i < n - 1; i++) {
        if (vals[i] > vals[i+1]) inc = 0;
        if (vals[i] < vals[i+1]) dec = 0;
    }
    return (inc || dec) ? 5 : 0;
}

static int monotonicity(const grid_t g) {
    int s = 0;
    for (int r = 0; r < N; r++)
        s += line_mono(g[r]);
    int col[N];
    for (int c = 0; c < N; c++) {
        for (int r = 0; r < N; r++) col[r] = g[r][c];
        s += line_mono(col);
    }
    return s;
}

static double smoothness(const grid_t g) {
    double penalty = 0;
    for (int r = 0; r < N; r++)
        for (int c = 0; c < N; c++) {
            int v = g[r][c];
            if (v == 0) continue;
            if (c + 1 < N && g[r][c+1] != 0)
                penalty += abs(v - g[r][c+1]);
            if (r + 1 < N && g[r+1][c] != 0)
                penalty += abs(v - g[r+1][c]);
        }
    return -penalty;
}

static double eval_grid(const grid_t g) {
    int empties = count_empty(g);
    int corner = corner_score(g);
    int mono = monotonicity(g);
    double smooth = smoothness(g);
    int mx = max_tile(g);
    return empties * 15.0 + corner * 2.5 + mono * 4.0 + smooth * 0.1 + mx * 0.01;
}

/* Encode cell value 0,2,4,...,2048 as 0..12 for cache key (4 bits per cell) */
static int val_to_code(int v) {
    if (v == 0) return 0;
    int c = 0;
    while (v > 1) { v /= 2; c++; }
    return c + 1; /* 2->1, 4->2, ..., 2048->12 */
}

static void grid_to_key(const grid_t g, int depth, int is_max, unsigned long long *klo, unsigned long long *khi) {
    *klo = 0;
    for (int r = 0; r < N; r++)
        for (int c = 0; c < N; c++)
            *klo = (*klo << 4) | (val_to_code(g[r][c]) & 15);
    *khi = (unsigned long long)(depth & 0xff) | ((unsigned long long)(is_max & 1) << 8);
}

static unsigned long long hash_key(unsigned long long klo, unsigned long long khi) {
    return (klo * 0x9e3779b97f4a7c15ULL) ^ (khi * 0x9e3779b9ULL);
}

static double cache_get(unsigned long long klo, unsigned long long khi) {
    cache_entry_t *cache = current_cache;
    if (!cache) return -1e300;
    unsigned long long h = hash_key(klo, khi) % CACHE_SIZE;
    for (int i = 0; i < CACHE_SIZE; i++) {
        int idx = (h + i) % CACHE_SIZE;
        if (!cache[idx].used) return -1e300;
        if (cache[idx].key_lo == klo && cache[idx].key_hi == khi)
            return cache[idx].value;
    }
    return -1e300;
}

static void cache_put(unsigned long long klo, unsigned long long khi, double value) {
    cache_entry_t *cache = current_cache;
    if (!cache) return;
    unsigned long long h = hash_key(klo, khi) % CACHE_SIZE;
    for (int i = 0; i < CACHE_SIZE; i++) {
        int idx = (h + i) % CACHE_SIZE;
        if (!cache[idx].used) {
            cache[idx].key_lo = klo;
            cache[idx].key_hi = khi;
            cache[idx].value = value;
            cache[idx].used = 1;
            return;
        }
        if (cache[idx].key_lo == klo && cache[idx].key_hi == khi) {
            cache[idx].value = value;
            return;
        }
    }
}

static void cache_clear(void) {
    if (current_cache)
        memset(current_cache, 0, CACHE_SIZE * sizeof(cache_entry_t));
}

static double expectimax(grid_t g, int depth, int is_max);

static double expectimax_impl(grid_t g, int depth, int is_max) {
    unsigned long long klo, khi;
    grid_to_key(g, depth, is_max, &klo, &khi);
    double cached = cache_get(klo, khi);
    if (cached > -1e299) return cached;

    if (depth == 0) {
        double v = eval_grid(g);
        cache_put(klo, khi, v);
        return v;
    }

    int empties = count_empty(g);
    if (empties == 0) {
        double v = eval_grid(g);
        cache_put(klo, khi, v);
        return v;
    }

    double result;
    if (is_max) {
        double best = -1e300;
        int any = 0;
        const int dirs[] = {0, 1, 2, 3}; /* up, right, down, left */
        for (int di = 0; di < 4; di++) {
            grid_t next;
            grid_copy(next, g);
            int score;
            if (!do_move(next, dirs[di], &score)) continue;
            any = 1;
            double here = eval_grid(next) + score * 0.1;
            double future = expectimax(next, depth - 1, 0);
            double total = here + GAMMA * future;
            if (total > best) best = total;
        }
        if (!any) best = eval_grid(g);
        result = best;
    } else {
        /* Chance node: sample empty cells. Use smaller cap at high depth to keep depth 9 feasible. */
        int cap = (depth >= 7 && max_empty_samples > 6) ? 6 : max_empty_samples;
        int cells[16][2], nc = 0;
        for (int r = 0; r < N; r++)
            for (int c = 0; c < N; c++)
                if (g[r][c] == 0) {
                    cells[nc][0] = r;
                    cells[nc][1] = c;
                    nc++;
                }
        /* Prefer lower rows (higher r) when trimming */
        if (nc > cap) {
            for (int i = 0; i < nc - 1; i++)
                for (int j = i + 1; j < nc; j++)
                    if (cells[j][0] > cells[i][0]) {
                        int t0 = cells[i][0], t1 = cells[i][1];
                        cells[i][0] = cells[j][0]; cells[i][1] = cells[j][1];
                        cells[j][0] = t0; cells[j][1] = t1;
                    }
            nc = cap;
        }
        double expected = 0, total_prob = 0;
        for (int i = 0; i < nc; i++) {
            int r = cells[i][0], c = cells[i][1];
            for (int val = 2; val <= 4; val += 2) {
                double prob = (val == 2) ? 0.9 : 0.1;
                grid_t g2;
                grid_copy(g2, g);
                g2[r][c] = val;
                expected += prob * expectimax(g2, depth - 1, 1);
                total_prob += prob;
            }
        }
        if (total_prob < 1e-9)
            result = eval_grid(g);
        else
            result = expected / total_prob;
    }
    cache_put(klo, khi, result);
    return result;
}

static double expectimax(grid_t g, int depth, int is_max) {
    return expectimax_impl(g, depth, is_max);
}

static const char *dir_name(int dir) {
    switch (dir) {
        case 0: return "up";
        case 1: return "right";
        case 2: return "down";
        case 3: return "left";
        default: return "left";
    }
}

typedef struct {
    grid_t grid;
    int dir;
    int depth;
    int thread_id;
    double result;
    int valid;
} worker_arg_t;

static void *worker(void *arg_) {
    worker_arg_t *arg = (worker_arg_t *)arg_;
    grid_t next;
    grid_copy(next, arg->grid);
    int score;
    if (!do_move(next, arg->dir, &score)) {
        arg->valid = 0;
        return NULL;
    }
    current_cache = caches[arg->thread_id];
    cache_clear();
    double here = eval_grid(next) + score * 0.1;
    double future = expectimax(next, arg->depth - 1, 0);
    arg->result = here + GAMMA * future;
    arg->valid = 1;
    return NULL;
}

int main(int argc, char **argv) {
    int timeout_sec = 0;
    if (argc >= 5) {
        depth_low    = atoi(argv[1]);
        depth_high   = atoi(argv[2]);
        serious_empty = atoi(argv[3]);
        serious_max_tile = atoi(argv[4]);
    }
    if (argc >= 6)
        max_empty_samples = atoi(argv[5]);
    if (argc >= 7)
        timeout_sec = atoi(argv[6]);

    grid_t grid;
    for (int r = 0; r < N; r++)
        for (int c = 0; c < N; c++)
            if (scanf("%d", &grid[r][c]) != 1)
                grid[r][c] = 0;

    for (int i = 0; i < NTHREADS; i++) {
        caches[i] = (cache_entry_t *)calloc(CACHE_SIZE, sizeof(cache_entry_t));
        if (!caches[i]) {
            for (int j = 0; j < i; j++) free(caches[j]);
            fprintf(stderr, "strategy_2048: failed to allocate cache\n");
            return 1;
        }
    }

    int empties = count_empty(grid);
    int mx = max_tile(grid);
    int serious = (empties <= serious_empty || mx >= serious_max_tile);
    int depth = serious ? depth_high : depth_low;

    const int dirs[] = {0, 1, 2, 3};
    int best_dir = -1;
    double best_score = -1e300;
    time_t start = time(NULL);

    if (timeout_sec > 0 && serious) {
        /* Iterative deepening: try depth_low..depth_high, stop when time runs out */
        for (int d = depth_low; d <= depth && (timeout_sec <= 0 || (time(NULL) - start) < timeout_sec); d++) {
            worker_arg_t args[NTHREADS];
            pthread_t threads[NTHREADS];
            for (int i = 0; i < NTHREADS; i++) {
                grid_copy(args[i].grid, grid);
                args[i].dir = dirs[i];
                args[i].depth = d;
                args[i].thread_id = i;
                args[i].valid = 0;
                pthread_create(&threads[i], NULL, worker, &args[i]);
            }
            for (int i = 0; i < NTHREADS; i++)
                pthread_join(threads[i], NULL);
            for (int i = 0; i < NTHREADS; i++) {
                if (args[i].valid && args[i].result > best_score) {
                    best_score = args[i].result;
                    best_dir = args[i].dir;
                }
            }
        }
    } else {
        worker_arg_t args[NTHREADS];
        pthread_t threads[NTHREADS];
        for (int i = 0; i < NTHREADS; i++) {
            grid_copy(args[i].grid, grid);
            args[i].dir = dirs[i];
            args[i].depth = depth;
            args[i].thread_id = i;
            args[i].valid = 0;
            pthread_create(&threads[i], NULL, worker, &args[i]);
        }
        for (int i = 0; i < NTHREADS; i++)
            pthread_join(threads[i], NULL);
        for (int i = 0; i < NTHREADS; i++) {
            if (args[i].valid && args[i].result > best_score) {
                best_score = args[i].result;
                best_dir = args[i].dir;
            }
        }
    }

    for (int i = 0; i < NTHREADS; i++)
        free(caches[i]);

    if (best_dir < 0) {
        printf("none\n");
        return 0;
    }
    printf("%s\n", dir_name(best_dir));
    return 0;
}
