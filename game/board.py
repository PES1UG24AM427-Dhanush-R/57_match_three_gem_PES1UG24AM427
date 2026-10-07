import random
import pygame

GRID_SIZE = 8
TILE_SIZE = 60
GEM_COLORS = [
    (220, 50, 50),   # Red
    (50, 200, 50),   # Green
    (50, 100, 240),  # Blue
    (240, 200, 40),  # Yellow
    (180, 50, 220),  # Purple
    (240, 130, 40),  # Orange
]


class Gem:
   
    def __init__(self, color, target_row, col):
        self.color = color
        self.target_row = target_row
        self.col = col
        self.current_y = (target_row - 2) * TILE_SIZE
        self.target_y = target_row * TILE_SIZE
        self.fall_speed = 12.0
        self.special = False       # True if this is a line-clear gem
        self.orientation = None    # 'row' or 'col' — which line it clears

    def update(self):
        if self.current_y < self.target_y:
            self.current_y += self.fall_speed
            if self.current_y > self.target_y:
                self.current_y = self.target_y

    def is_animating(self):
        return self.current_y < self.target_y


class Board:

    def __init__(self, offset_x, offset_y, target_score=500, max_moves=20):
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.target_score = target_score
        self.max_moves = max_moves
        self.grid = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.selected = None
        self.score = 0
        self.moves_remaining = max_moves
        self.reset()

    def reset(self):
        self.score = 0
        self.moves_remaining = self.max_moves
        self.selected = None
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                color = random.choice(GEM_COLORS)
                gem = Gem(color, r, c)
                gem.current_y = gem.target_y  
                self.grid[r][c] = gem

        self.resolve_matches()

    def is_animating(self):
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c] and self.grid[r][c].is_animating():
                    return True
        return False

    def swap_gems(self, pos1, pos2):
        r1, c1 = pos1
        r2, c2 = pos2

        g1, g2 = self.grid[r1][c1], self.grid[r2][c2]
        self.grid[r1][c1], self.grid[r2][c2] = g2, g1

        if self.grid[r1][c1]:
            self.grid[r1][c1].target_row = r1
            self.grid[r1][c1].target_y = r1 * TILE_SIZE
            self.grid[r1][c1].current_y = r1 * TILE_SIZE

        if self.grid[r2][c2]:
            self.grid[r2][c2].target_row = r2
            self.grid[r2][c2].target_y = r2 * TILE_SIZE
            self.grid[r2][c2].current_y = r2 * TILE_SIZE

    def is_adjacent(self, pos1, pos2):
        r1, c1 = pos1
        r2, c2 = pos2
        return abs(r1 - r2) + abs(c1 - c2) == 1

    def find_matches(self):
        matched = set()
        specials = []  # list of (r, c, orientation) for gems to promote to special

        # Horizontal runs
        for r in range(GRID_SIZE):
            c = 0
            while c < GRID_SIZE:
                if not self.grid[r][c]:
                    c += 1
                    continue
                run_color = self.grid[r][c].color
                run_start = c
                while c < GRID_SIZE and self.grid[r][c] and self.grid[r][c].color == run_color:
                    c += 1
                run_len = c - run_start
                if run_len >= 3:
                    cells = [(r, col) for col in range(run_start, run_start + run_len)]
                    if run_len >= 4:
                        # Pick the middle cell to become the special gem; mark rest for clearing
                        mid = run_start + run_len // 2
                        specials.append((r, mid, 'row'))
                        for cell in cells:
                            if cell != (r, mid):
                                matched.add(cell)
                    else:
                        matched.update(cells)

        # Vertical runs
        for c in range(GRID_SIZE):
            r = 0
            while r < GRID_SIZE:
                if not self.grid[r][c]:
                    r += 1
                    continue
                run_color = self.grid[r][c].color
                run_start = r
                while r < GRID_SIZE and self.grid[r][c] and self.grid[r][c].color == run_color:
                    r += 1
                run_len = r - run_start
                if run_len >= 3:
                    cells = [(row, c) for row in range(run_start, run_start + run_len)]
                    if run_len >= 4:
                        mid = run_start + run_len // 2
                        specials.append((mid, c, 'col'))
                        for cell in cells:
                            if cell != (mid, c):
                                matched.add(cell)
                    else:
                        matched.update(cells)

        # Don't mark special-gem cells for immediate clearing; they stay on the board
        # But if a special gem itself is in the matched set (caught by a 3-match), keep it
        return matched, specials

    def drop_and_refill(self):
        for c in range(GRID_SIZE):
            empty_slots = 0
            for r in range(GRID_SIZE - 1, -1, -1):
                if self.grid[r][c] is None:
                    empty_slots += 1
                elif empty_slots > 0:
                    gem = self.grid[r][c]
                    gem.target_row = r + empty_slots
                    gem.target_y = (r + empty_slots) * TILE_SIZE
                    self.grid[r + empty_slots][c] = gem
                    self.grid[r][c] = None

            for r in range(empty_slots):
                color = random.choice(GEM_COLORS)
                gem = Gem(color, r, c)
                gem.current_y = -((empty_slots - r) * TILE_SIZE)
                self.grid[r][c] = gem

    def resolve_matches(self):
        total_score = 0
        cascade = 1
        while True:
            matches, specials = self.find_matches()

            # Promote gems to special (4-in-a-row) — do this before clearing
            for r, c, orientation in specials:
                gem = self.grid[r][c]
                if gem and not gem.special:
                    gem.special = True
                    gem.orientation = orientation

            # If a special gem is in the matched set, detonate its line
            extra_clears = set()
            for r, c in list(matches):
                gem = self.grid[r][c]
                if gem and gem.special:
                    if gem.orientation == 'row':
                        for cc in range(GRID_SIZE):
                            extra_clears.add((r, cc))
                    else:
                        for rr in range(GRID_SIZE):
                            extra_clears.add((rr, c))
            matches.update(extra_clears)

            if not matches and not specials:
                break

            if not matches:
                # Only specials were created this round, no cells to clear
                break

            total_score += len(matches) * 10 * cascade
            cascade += 1
            for r, c in matches:
                self.grid[r][c] = None
            self.drop_and_refill()
        return total_score

    def process_swap(self, pos1, pos2):
        if not self.is_adjacent(pos1, pos2) or self.is_game_over() or self.is_animating():
            return False

        self.swap_gems(pos1, pos2)
        matches, specials = self.find_matches()

        if not matches and not specials:
            self.swap_gems(pos1, pos2)
            return False

        self.moves_remaining -= 1
        score_gained = self.resolve_matches()
        self.score += score_gained
        return True

    def is_game_over(self):
        return self.score >= self.target_score or self.moves_remaining <= 0

    def check_result(self):
        if self.score >= self.target_score:
            return "WIN"
        if self.moves_remaining <= 0:
            return "LOSS"
        return None

    def update(self):
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c]:
                    self.grid[r][c].update()

    def render(self, surface):
        board_rect = pygame.Rect(
            self.offset_x, self.offset_y, GRID_SIZE * TILE_SIZE, GRID_SIZE * TILE_SIZE
        )
        pygame.draw.rect(surface, (20, 22, 28), board_rect, border_radius=8)
        pygame.draw.rect(surface, (60, 65, 75), board_rect, width=3, border_radius=8)

        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                gem = self.grid[r][c]
                if gem:
                    x = self.offset_x + c * TILE_SIZE
                    y = self.offset_y + gem.current_y
                    tile_rect = pygame.Rect(x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4)

                    pygame.draw.rect(surface, gem.color, tile_rect, border_radius=10)
                    pygame.draw.rect(
                        surface, (255, 255, 255), tile_rect, width=1, border_radius=10
                    )
                    # Draw glowing star/circle for special line-clear gems
                    if gem.special:
                        cx = x + TILE_SIZE // 2
                        cy = y + TILE_SIZE // 2
                        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), 10)
                        pygame.draw.circle(surface, (255, 240, 80), (cx, cy), 6)

                if self.selected == (r, c):
                    sel_x = self.offset_x + c * TILE_SIZE
                    sel_y = self.offset_y + r * TILE_SIZE
                    sel_rect = pygame.Rect(sel_x + 2, sel_y + 2, TILE_SIZE - 4, TILE_SIZE - 4)
                    pygame.draw.rect(
                        surface, (255, 255, 255), sel_rect, width=4, border_radius=10
                    )
