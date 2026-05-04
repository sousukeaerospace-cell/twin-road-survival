#!/usr/bin/env python3
"""
ツイン・ロード・サバイバル：ラスト・ディフェンス
Twin Road Survival: Last Defense

Python 3 + Pygame のみで動作する単一ファイルゲーム
画像・音声ファイル不要（全て図形描画）
"""

import pygame
import sys
import random
import math
from enum import Enum

# ── 定数 ──────────────────────────────────────────────
SCREEN_W, SCREEN_H = 900, 700
FPS = 60

# 色
BLACK   = (0, 0, 0)
WHITE   = (255, 255, 255)
GRAY    = (100, 100, 100)
DARK_GRAY = (60, 60, 60)
YELLOW  = (255, 220, 0)
GREEN   = (50, 200, 50)
DARK_GREEN = (30, 140, 30)
RED     = (220, 40, 40)
DARK_RED = (140, 20, 20)
PURPLE  = (160, 40, 200)
BLUE    = (60, 120, 255)
CYAN    = (0, 220, 255)
ORANGE  = (255, 160, 30)
BROWN   = (120, 80, 40)
LIGHT_GRAY = (180, 180, 180)
SKY_DARK = (30, 25, 40)
BUILDING_COLOR = (50, 45, 55)
BUILDING_DARK = (35, 30, 40)
WINDOW_COLOR = (80, 70, 50)
GOLD    = (255, 215, 0)
SHIELD_COLOR = (80, 180, 255, 120)
HEAL_GREEN = (80, 255, 80)
PINK    = (255, 100, 150)

# レーン設定
ROAD_LEFT = 250
ROAD_RIGHT = 650
ROAD_CENTER = (ROAD_LEFT + ROAD_RIGHT) // 2
LANE_LEFT_X = (ROAD_LEFT + ROAD_CENTER) // 2
LANE_RIGHT_X = (ROAD_CENTER + ROAD_RIGHT) // 2
LANE_WIDTH = (ROAD_RIGHT - ROAD_LEFT) // 2

# HUD
HUD_HEIGHT = 80
ITEM_SLOT_Y = SCREEN_H - 70
ITEM_SLOT_SIZE = 50

# ── ウェーブ定義 ──────────────────────────────────────
WAVE_DEFINITIONS = [
    # wave 1: easy
    {"enemies": [("zombie", 8, 0.6)], "delay": 60, "message": "WAVE 1 - 前哨戦"},
    # wave 2
    {"enemies": [("zombie", 10, 0.7), ("soldier", 3, 0.5)], "delay": 50, "message": "WAVE 2 - 増援"},
    # wave 3
    {"enemies": [("zombie", 12, 0.8), ("soldier", 6, 0.6)], "delay": 40, "message": "WAVE 3 - 猛攻"},
    # wave 4
    {"enemies": [("zombie", 15, 1.0), ("soldier", 8, 0.7), ("fast_zombie", 5, 1.2)], "delay": 35, "message": "WAVE 4 - 死の行軍"},
    # wave 5: boss
    {"enemies": [("zombie", 8, 0.8), ("soldier", 4, 0.6)], "boss": True, "delay": 45, "message": "WAVE 5 - BOSS: デスロード"},
]


class GameState(Enum):
    TITLE = 0
    PLAYING = 1
    WAVE_INTRO = 2
    GAME_OVER = 3
    GAME_CLEAR = 4


# ── ユーティリティ ──────────────────────────────────────
class DamagePopup:
    def __init__(self, x, y, damage, color=WHITE):
        self.x = x
        self.y = y
        self.damage = damage
        self.color = color
        self.timer = 40
        self.vy = -2

    def update(self):
        self.y += self.vy
        self.vy += 0.05
        self.timer -= 1
        return self.timer > 0

    def draw(self, screen, font):
        alpha = min(255, self.timer * 8)
        text = font.render(str(self.damage), True, self.color)
        screen.blit(text, (self.x - text.get_width() // 2, int(self.y)))


class Particle:
    def __init__(self, x, y, color, vx=0, vy=0, life=30, size=3):
        self.x = x
        self.y = y
        self.color = color
        self.vx = vx + random.uniform(-1, 1)
        self.vy = vy + random.uniform(-2, 0)
        self.life = life
        self.max_life = life
        self.size = size

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.1
        self.life -= 1
        return self.life > 0

    def draw(self, screen):
        alpha = self.life / self.max_life
        r = max(1, int(self.size * alpha))
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), r)


class Coin:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.timer = 60
        self.vy = -1

    def update(self):
        self.y += self.vy
        self.vy += 0.08
        self.timer -= 1
        return self.timer > 0

    def draw(self, screen, font):
        pygame.draw.circle(screen, GOLD, (int(self.x), int(self.y)), 8)
        pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), 5)
        text = font.render("+1", True, GOLD)
        screen.blit(text, (int(self.x) + 10, int(self.y) - 8))


# ── 弾丸 ──────────────────────────────────────────────
class Bullet:
    def __init__(self, x, y, target_x, target_y, damage=10, speed=8, color=YELLOW):
        self.x = x
        self.y = y
        dx = target_x - x
        dy = target_y - y
        dist = max(1, math.sqrt(dx*dx + dy*dy))
        self.vx = dx / dist * speed
        self.vy = dy / dist * speed
        self.damage = damage
        self.color = color
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.y < 0 or self.y > SCREEN_H or self.x < 0 or self.x > SCREEN_W:
            self.alive = False

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), 3)
        # trail
        tx = self.x - self.vx * 0.5
        ty = self.y - self.vy * 0.5
        pygame.draw.line(screen, self.color, (int(self.x), int(self.y)), (int(tx), int(ty)), 2)


class EnemyBullet:
    def __init__(self, x, y, target_x, target_y, damage=5, speed=4, color=RED):
        self.x = x
        self.y = y
        dx = target_x - x
        dy = target_y - y
        dist = max(1, math.sqrt(dx*dx + dy*dy))
        self.vx = dx / dist * speed
        self.vy = dy / dist * speed
        self.damage = damage
        self.color = color
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.y < 0 or self.y > SCREEN_H or self.x < 0 or self.x > SCREEN_W:
            self.alive = False

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), 4)
        pygame.draw.circle(screen, ORANGE, (int(self.x), int(self.y)), 2)


# ── 兵士ユニット ──────────────────────────────────────
class Soldier:
    def __init__(self, x, y, lane):
        self.x = x
        self.y = y
        self.lane = lane  # 0=left, 1=right
        self.fire_cooldown = 0
        self.fire_rate = 20  # frames between shots
        self.damage = 8
        self.range = 350
        self.alive = True

    def update(self, enemies, bullets, focused_lane):
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        # 射程内の敵を探す（集中先レーン優先）
        target = None
        min_dist = self.range

        # まず集中レーンの敵
        for e in enemies:
            if not e.alive:
                continue
            if e.lane == focused_lane:
                dist = math.sqrt((self.x - e.x)**2 + (self.y - e.y)**2)
                if dist < min_dist:
                    min_dist = dist
                    target = e

        # 集中レーンに敵がいなければ他も
        if target is None:
            for e in enemies:
                if not e.alive:
                    continue
                dist = math.sqrt((self.x - e.x)**2 + (self.y - e.y)**2)
                if dist < min_dist:
                    min_dist = dist
                    target = e

        if target and self.fire_cooldown <= 0:
            bullets.append(Bullet(self.x, self.y - 8, target.x, target.y, self.damage))
            self.fire_cooldown = self.fire_rate

    def draw(self, screen):
        # 体
        pygame.draw.rect(screen, GREEN, (self.x - 8, self.y - 12, 16, 20))
        # 頭
        pygame.draw.circle(screen, GREEN, (self.x, self.y - 16), 6)
        # ヘルメット
        pygame.draw.arc(screen, DARK_GREEN, (self.x - 7, self.y - 23, 14, 12), 0, math.pi, 3)
        # 銃
        pygame.draw.rect(screen, DARK_GRAY, (self.x + 6, self.y - 14, 12, 3))


# ── 敵 ──────────────────────────────────────────────
class Enemy:
    def __init__(self, x, y, lane, enemy_type="zombie"):
        self.x = x
        self.y = y
        self.lane = lane
        self.enemy_type = enemy_type
        self.alive = True
        self.flash_timer = 0

        if enemy_type == "zombie":
            self.hp = 30
            self.max_hp = 30
            self.speed = 0.5
            self.damage = 10
            self.color = RED
            self.coin_value = 1
            self.size = 12
            self.attack_range = 60
            self.attack_cooldown = 0
            self.attack_rate = 90
        elif enemy_type == "fast_zombie":
            self.hp = 20
            self.max_hp = 20
            self.speed = 1.2
            self.damage = 8
            self.color = PURPLE
            self.coin_value = 2
            self.size = 10
            self.attack_range = 50
            self.attack_cooldown = 0
            self.attack_rate = 60
        elif enemy_type == "soldier":
            self.hp = 50
            self.max_hp = 50
            self.speed = 0.3
            self.damage = 15
            self.color = DARK_RED
            self.coin_value = 3
            self.size = 14
            self.attack_range = 200
            self.attack_cooldown = 0
            self.attack_rate = 60
            self.shoots = True

    def update(self, commander_y, enemy_bullets, soldiers):
        if not self.alive:
            return
        if self.flash_timer > 0:
            self.flash_timer -= 1

        # 攻撃クールダウン
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        # 前進
        self.y += self.speed

        # 兵士への攻撃（soldier type は射撃）
        if hasattr(self, 'shoots') and self.shoots:
            for s in soldiers:
                if not s.alive:
                    continue
                dist = math.sqrt((self.x - s.x)**2 + (self.y - s.y)**2)
                if dist < self.attack_range and self.attack_cooldown <= 0:
                    enemy_bullets.append(EnemyBullet(self.x, self.y, s.x, s.y, self.damage))
                    self.attack_cooldown = self.attack_rate
                    break

    def take_damage(self, dmg):
        self.hp -= dmg
        self.flash_timer = 5
        if self.hp <= 0:
            self.alive = False

    def draw(self, screen):
        if not self.alive:
            return
        s = self.size
        color = WHITE if self.flash_timer > 0 else self.color

        if self.enemy_type == "zombie":
            # 体
            pygame.draw.rect(screen, color, (self.x - s//2, self.y - s, s, s * 2))
            # 頭
            pygame.draw.circle(screen, color, (self.x, self.y - s - 4), s // 2 + 2)
            # 腕（前に伸ばす）
            pygame.draw.line(screen, color, (self.x - s//2, self.y - s//2),
                           (self.x - s, self.y + 4), 3)
            pygame.draw.line(screen, color, (self.x + s//2, self.y - s//2),
                           (self.x + s, self.y + 4), 3)
        elif self.enemy_type == "fast_zombie":
            # 素早いゾンビ - 紫色、小さい
            pygame.draw.ellipse(screen, color, (self.x - s//2, self.y - s, s, s * 2))
            pygame.draw.circle(screen, color, (self.x, self.y - s - 3), s // 2 + 1)
            # 走っている腕
            offset = math.sin(pygame.time.get_ticks() * 0.01) * 5
            pygame.draw.line(screen, color, (self.x - 4, self.y - 4),
                           (self.x - 10 + offset, self.y + 6), 2)
            pygame.draw.line(screen, color, (self.x + 4, self.y - 4),
                           (self.x + 10 - offset, self.y + 6), 2)
        elif self.enemy_type == "soldier":
            # 敵兵 - ダークレッド、銃を持つ
            pygame.draw.rect(screen, color, (self.x - s//2, self.y - s, s, s * 2))
            pygame.draw.circle(screen, color, (self.x, self.y - s - 5), s // 2 + 2)
            # ヘルメット
            pygame.draw.rect(screen, DARK_GRAY, (self.x - s//2 - 1, self.y - s - 10, s + 2, 6))
            # 銃
            pygame.draw.rect(screen, DARK_GRAY, (self.x - s, self.y - 2, s, 3))

        # HPバー
        if self.hp < self.max_hp:
            bar_w = s * 2
            bar_h = 3
            pygame.draw.rect(screen, DARK_RED, (self.x - bar_w//2, self.y - s - 14, bar_w, bar_h))
            hp_w = int(bar_w * self.hp / self.max_hp)
            pygame.draw.rect(screen, RED, (self.x - bar_w//2, self.y - s - 14, hp_w, bar_h))


# ── ボス ──────────────────────────────────────────────
class Boss:
    def __init__(self):
        self.x = ROAD_CENTER
        self.y = -60
        self.target_y = 120
        self.hp = 500
        self.max_hp = 500
        self.alive = True
        self.speed = 0.3
        self.phase = 0  # 0=entering, 1=fighting
        self.attack_timer = 0
        self.attack_pattern = 0
        self.flash_timer = 0
        self.size = 40
        self.lane = -1  # both

    def update(self, enemy_bullets, commander, soldiers):
        if not self.alive:
            return
        if self.flash_timer > 0:
            self.flash_timer -= 1

        if self.phase == 0:
            self.y += 1
            if self.y >= self.target_y:
                self.y = self.target_y
                self.phase = 1
        elif self.phase == 1:
            self.attack_timer += 1

            # 攻撃パターン切り替え
            if self.attack_timer % 120 == 0:
                # 両レーン射撃
                for tx in [LANE_LEFT_X, LANE_RIGHT_X]:
                    for _ in range(3):
                        bx = self.x + random.randint(-20, 20)
                        by = self.y + 30
                        enemy_bullets.append(
                            EnemyBullet(bx, by, tx + random.randint(-30, 30),
                                       commander.y, 12, 3, PURPLE))

            if self.attack_timer % 180 == 90:
                # 範囲散弾
                for angle in range(0, 360, 30):
                    rad = math.radians(angle)
                    vx = math.cos(rad) * 3
                    vy = math.sin(rad) * 3 + 1
                    b = EnemyBullet(self.x, self.y + 20,
                                    self.x + vx * 100, self.y + 20 + vy * 100,
                                    8, 3, ORANGE)
                    enemy_bullets.append(b)

            # ゆっくり左右に動く
            self.x = ROAD_CENTER + math.sin(self.attack_timer * 0.02) * 80

    def take_damage(self, dmg):
        self.hp -= dmg
        self.flash_timer = 5
        if self.hp <= 0:
            self.alive = False

    def draw(self, screen):
        if not self.alive:
            return
        s = self.size
        color = WHITE if self.flash_timer > 0 else DARK_RED

        # 巨大な体
        pygame.draw.rect(screen, color, (self.x - s, self.y - s, s * 2, s * 2), border_radius=8)
        pygame.draw.rect(screen, BLACK, (self.x - s + 3, self.y - s + 3, s * 2 - 6, s * 2 - 6), border_radius=6)
        pygame.draw.rect(screen, color, (self.x - s + 6, self.y - s + 6, s * 2 - 12, s * 2 - 12), border_radius=4)

        # 頭部
        pygame.draw.circle(screen, color, (self.x, self.y - s - 15), 20)
        # 目（赤く光る）
        pygame.draw.circle(screen, ORANGE, (self.x - 8, self.y - s - 18), 5)
        pygame.draw.circle(screen, ORANGE, (self.x + 8, self.y - s - 18), 5)
        pygame.draw.circle(screen, YELLOW, (self.x - 8, self.y - s - 18), 2)
        pygame.draw.circle(screen, YELLOW, (self.x + 8, self.y - s - 18), 2)

        # 角
        pygame.draw.polygon(screen, DARK_RED, [
            (self.x - 15, self.y - s - 30),
            (self.x - 20, self.y - s - 55),
            (self.x - 5, self.y - s - 30),
        ])
        pygame.draw.polygon(screen, DARK_RED, [
            (self.x + 15, self.y - s - 30),
            (self.x + 20, self.y - s - 55),
            (self.x + 5, self.y - s - 30),
        ])

        # 腕
        pygame.draw.rect(screen, color, (self.x - s - 15, self.y - s + 10, 18, 50), border_radius=5)
        pygame.draw.rect(screen, color, (self.x + s - 3, self.y - s + 10, 18, 50), border_radius=5)

        # HPバー（大きめ）
        bar_w = 120
        bar_h = 8
        bx = self.x - bar_w // 2
        by = self.y - s - 65
        pygame.draw.rect(screen, DARK_GRAY, (bx - 1, by - 1, bar_w + 2, bar_h + 2))
        pygame.draw.rect(screen, DARK_RED, (bx, by, bar_w, bar_h))
        hp_w = int(bar_w * max(0, self.hp) / self.max_hp)
        pygame.draw.rect(screen, RED, (bx, by, hp_w, bar_h))


# ── 指揮官（プレイヤー） ──────────────────────────────
class Commander:
    def __init__(self):
        self.x = ROAD_CENTER
        self.y = SCREEN_H - 130
        self.hp = 100
        self.max_hp = 100
        self.focused_lane = 0  # 0=left, 1=right
        self.shield_timer = 0
        self.flash_timer = 0
        self.coins = 0

    def take_damage(self, dmg):
        if self.shield_timer > 0:
            return
        self.hp -= dmg
        self.flash_timer = 10
        if self.hp <= 0:
            self.hp = 0

    def draw(self, screen):
        # 指揮官の位置をフォーカスレーンに合わせる
        target_x = LANE_LEFT_X if self.focused_lane == 0 else LANE_RIGHT_X
        self.x += (target_x - self.x) * 0.15

        color = WHITE if self.flash_timer > 0 else BLUE
        if self.flash_timer > 0:
            self.flash_timer -= 1

        # 体
        pygame.draw.rect(screen, color, (self.x - 12, self.y - 10, 24, 28), border_radius=4)
        # 頭
        pygame.draw.circle(screen, color, (int(self.x), self.y - 16), 10)
        # 帽子（指揮官帽）
        pygame.draw.rect(screen, DARK_GRAY, (self.x - 14, self.y - 26, 28, 6))
        pygame.draw.rect(screen, GOLD, (self.x - 10, self.y - 30, 20, 6))
        # 星章
        pygame.draw.circle(screen, GOLD, (int(self.x), self.y - 2), 4)

        # 方向指示矢印
        arrow_x = target_x
        arrow_y = self.y - 50
        pygame.draw.polygon(screen, CYAN, [
            (arrow_x, arrow_y - 15),
            (arrow_x - 10, arrow_y),
            (arrow_x + 10, arrow_y),
        ])

        # シールドエフェクト
        if self.shield_timer > 0:
            shield_surface = pygame.Surface((60, 80), pygame.SRCALPHA)
            alpha = 100 + int(50 * math.sin(pygame.time.get_ticks() * 0.01))
            pygame.draw.ellipse(shield_surface, (80, 180, 255, alpha), (0, 0, 60, 80), 3)
            screen.blit(shield_surface, (int(self.x) - 30, self.y - 35))


# ── 爆発エフェクト ──────────────────────────────────────
class Explosion:
    def __init__(self, x, y, radius=60, damage=80):
        self.x = x
        self.y = y
        self.radius = radius
        self.damage = damage
        self.timer = 30
        self.max_timer = 30

    def update(self):
        self.timer -= 1
        return self.timer > 0

    def draw(self, screen):
        progress = 1 - self.timer / self.max_timer
        r = int(self.radius * min(1.0, progress * 2))
        alpha = int(200 * (self.timer / self.max_timer))

        # 複数円で爆発表現
        if progress < 0.5:
            pygame.draw.circle(screen, ORANGE, (int(self.x), int(self.y)), r)
            pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), r // 2)
            pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), r // 4)
        else:
            c = max(0, int(200 * (self.timer / self.max_timer)))
            pygame.draw.circle(screen, (c, c // 2, 0), (int(self.x), int(self.y)), r)
            pygame.draw.circle(screen, (c, c, 0), (int(self.x), int(self.y)), r // 2)


# ── ポータルエフェクト ──────────────────────────────────
class PortalEffect:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.timer = 40

    def update(self):
        self.timer -= 1
        return self.timer > 0

    def draw(self, screen):
        r = 30 - int(20 * (self.timer / 40))
        pygame.draw.circle(screen, CYAN, (int(self.x), int(self.y)), r + 10, 2)
        pygame.draw.circle(screen, BLUE, (int(self.x), int(self.y)), r, 2)
        for i in range(6):
            angle = math.radians(i * 60 + self.timer * 9)
            px = self.x + math.cos(angle) * (r + 5)
            py = self.y + math.sin(angle) * (r + 5)
            pygame.draw.circle(screen, CYAN, (int(px), int(py)), 3)


# ── アイテム定義 ──────────────────────────────────────
ITEMS = [
    {"name": "ポータル", "cost": 5, "color": CYAN, "icon": "P"},
    {"name": "爆撃", "cost": 8, "color": ORANGE, "icon": "B"},
    {"name": "メディカル", "cost": 4, "color": HEAL_GREEN, "icon": "M"},
    {"name": "シールド", "cost": 6, "color": BLUE, "icon": "S"},
]


# ── メインゲームクラス ──────────────────────────────────
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("ツイン・ロード・サバイバル：ラスト・ディフェンス")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("msgothic", 18)
        self.font_large = pygame.font.SysFont("msgothic", 36)
        self.font_title = pygame.font.SysFont("msgothic", 48)
        self.font_small = pygame.font.SysFont("msgothic", 14)

        self.reset()

    def reset(self):
        self.state = GameState.TITLE
        self.commander = Commander()
        self.soldiers = []
        self.enemies = []
        self.boss = None
        self.bullets = []
        self.enemy_bullets = []
        self.particles = []
        self.popups = []
        self.coins_anim = []
        self.explosions = []
        self.portal_effects = []

        self.current_wave = 0
        self.wave_timer = 0
        self.wave_intro_timer = 0
        self.spawn_queue = []
        self.spawn_timer = 0
        self.wave_complete = False

        self.road_offset = 0  # ストライプアニメーション用

        self.dragging_item = None
        self.drag_pos = (0, 0)

        # 初期兵士配置
        self._spawn_initial_soldiers()

    def _spawn_initial_soldiers(self):
        self.soldiers = []
        positions = [
            (LANE_LEFT_X - 20, SCREEN_H - 200, 0),
            (LANE_LEFT_X + 20, SCREEN_H - 180, 0),
            (LANE_RIGHT_X - 20, SCREEN_H - 200, 1),
            (LANE_RIGHT_X + 20, SCREEN_H - 180, 1),
        ]
        for x, y, lane in positions:
            self.soldiers.append(Soldier(x, y, lane))

    def start_wave(self):
        if self.current_wave >= len(WAVE_DEFINITIONS):
            self.state = GameState.GAME_CLEAR
            return

        wave = WAVE_DEFINITIONS[self.current_wave]
        self.spawn_queue = []
        self.wave_complete = False

        for enemy_type, count, speed_mult in wave["enemies"]:
            for i in range(count):
                lane = random.randint(0, 1)
                delay = i * wave["delay"] + random.randint(0, 20)
                self.spawn_queue.append((delay, enemy_type, lane, speed_mult))

        # ボス
        if wave.get("boss"):
            self.boss = Boss()

        self.spawn_timer = 0
        self.state = GameState.WAVE_INTRO
        self.wave_intro_timer = 120  # 2秒

    def spawn_enemy(self, enemy_type, lane, speed_mult):
        lane_x = LANE_LEFT_X if lane == 0 else LANE_RIGHT_X
        x = lane_x + random.randint(-20, 20)
        e = Enemy(x, -20, lane, enemy_type)
        e.speed *= speed_mult
        self.enemies.append(e)

    def use_item(self, item_idx, lane):
        item = ITEMS[item_idx]
        if self.commander.coins < item["cost"]:
            return False

        self.commander.coins -= item["cost"]
        lane_x = LANE_LEFT_X if lane == 0 else LANE_RIGHT_X

        if item_idx == 0:  # ポータル（追加兵士）
            y_pos = SCREEN_H - 200 + random.randint(-20, 20)
            new_soldier = Soldier(lane_x + random.randint(-15, 15), y_pos, lane)
            self.soldiers.append(new_soldier)
            self.portal_effects.append(PortalEffect(lane_x, y_pos))

        elif item_idx == 1:  # 爆撃
            exp = Explosion(lane_x, 200, 80, 100)
            self.explosions.append(exp)
            # ダメージ適用
            for e in self.enemies:
                if not e.alive:
                    continue
                dist = math.sqrt((e.x - lane_x)**2 + (e.y - 200)**2)
                if dist < 80:
                    dmg = int(100 * (1 - dist / 80))
                    e.take_damage(dmg)
                    self.popups.append(DamagePopup(e.x, e.y - 20, dmg, ORANGE))
                    if not e.alive:
                        self.commander.coins += e.coin_value
                        self.coins_anim.append(Coin(e.x, e.y))
                        self._spawn_death_particles(e)
            if self.boss and self.boss.alive:
                dist = math.sqrt((self.boss.x - lane_x)**2 + (self.boss.y - 200)**2)
                if dist < 100:
                    dmg = int(80 * (1 - dist / 100))
                    self.boss.take_damage(dmg)
                    self.popups.append(DamagePopup(self.boss.x, self.boss.y - 30, dmg, ORANGE))
            # パーティクル
            for _ in range(30):
                self.particles.append(Particle(
                    lane_x + random.randint(-40, 40),
                    200 + random.randint(-40, 40),
                    random.choice([ORANGE, YELLOW, RED]),
                    random.uniform(-4, 4), random.uniform(-5, 1),
                    random.randint(20, 40), random.randint(2, 5)))

        elif item_idx == 2:  # メディカルパック
            heal = 30
            self.commander.hp = min(self.commander.max_hp, self.commander.hp + heal)
            self.popups.append(DamagePopup(self.commander.x, self.commander.y - 30, f"+{heal}", HEAL_GREEN))
            for _ in range(15):
                self.particles.append(Particle(
                    self.commander.x + random.randint(-20, 20),
                    self.commander.y + random.randint(-20, 20),
                    HEAL_GREEN, 0, -1, 30, 3))

        elif item_idx == 3:  # シールド
            self.commander.shield_timer = 300  # 5秒
            for _ in range(20):
                angle = random.uniform(0, math.pi * 2)
                self.particles.append(Particle(
                    self.commander.x + math.cos(angle) * 25,
                    self.commander.y + math.sin(angle) * 25,
                    CYAN, math.cos(angle) * 2, math.sin(angle) * 2, 30, 3))

        return True

    def _spawn_death_particles(self, entity):
        for _ in range(12):
            self.particles.append(Particle(
                entity.x + random.randint(-5, 5),
                entity.y + random.randint(-5, 5),
                entity.color if hasattr(entity, 'color') else RED,
                random.uniform(-3, 3), random.uniform(-3, 1),
                random.randint(15, 30), random.randint(2, 4)))

    def update(self):
        if self.state == GameState.WAVE_INTRO:
            self.wave_intro_timer -= 1
            if self.wave_intro_timer <= 0:
                self.state = GameState.PLAYING
            return

        if self.state != GameState.PLAYING:
            return

        # ロードアニメーション
        self.road_offset = (self.road_offset + 1) % 40

        # シールドタイマー
        if self.commander.shield_timer > 0:
            self.commander.shield_timer -= 1

        # 敵スポーン
        self.spawn_timer += 1
        new_queue = []
        for delay, etype, lane, smult in self.spawn_queue:
            if self.spawn_timer >= delay:
                self.spawn_enemy(etype, lane, smult)
            else:
                new_queue.append((delay, etype, lane, smult))
        self.spawn_queue = new_queue

        # 兵士更新
        for s in self.soldiers:
            if s.alive:
                all_targets = list(self.enemies)
                if self.boss and self.boss.alive:
                    # ボスも射撃対象に（ダミーのlane属性使用）
                    all_targets_with_boss = all_targets
                    s.update(all_targets_with_boss, self.bullets, self.commander.focused_lane)
                    # ボスへの射撃
                    if s.fire_cooldown == s.fire_rate - 1:
                        pass  # 既にupdateで処理
                else:
                    s.update(all_targets, self.bullets, self.commander.focused_lane)

        # ボスへの弾丸ターゲッティング補助
        if self.boss and self.boss.alive:
            for s in self.soldiers:
                if s.alive and s.fire_cooldown <= 0:
                    # ボスが近い場合ボスを狙う
                    dist_boss = math.sqrt((s.x - self.boss.x)**2 + (s.y - self.boss.y)**2)
                    if dist_boss < s.range:
                        has_closer_enemy = False
                        for e in self.enemies:
                            if e.alive:
                                de = math.sqrt((s.x - e.x)**2 + (s.y - e.y)**2)
                                if de < dist_boss:
                                    has_closer_enemy = True
                                    break
                        if not has_closer_enemy:
                            self.bullets.append(Bullet(s.x, s.y - 8, self.boss.x, self.boss.y, s.damage))
                            s.fire_cooldown = s.fire_rate

        # 弾丸更新
        for b in self.bullets:
            b.update()
            if not b.alive:
                continue
            # 敵との衝突判定
            for e in self.enemies:
                if not e.alive:
                    continue
                dist = math.sqrt((b.x - e.x)**2 + (b.y - e.y)**2)
                if dist < e.size + 5:
                    e.take_damage(b.damage)
                    self.popups.append(DamagePopup(e.x + random.randint(-10, 10),
                                                    e.y - 15, b.damage, YELLOW))
                    b.alive = False
                    if not e.alive:
                        self.commander.coins += e.coin_value
                        self.coins_anim.append(Coin(e.x, e.y))
                        self._spawn_death_particles(e)
                    break
            # ボスとの衝突
            if b.alive and self.boss and self.boss.alive:
                dist = math.sqrt((b.x - self.boss.x)**2 + (b.y - self.boss.y)**2)
                if dist < self.boss.size + 10:
                    self.boss.take_damage(b.damage)
                    self.popups.append(DamagePopup(
                        self.boss.x + random.randint(-15, 15),
                        self.boss.y - 30, b.damage, YELLOW))
                    b.alive = False
                    if not self.boss.alive:
                        self.commander.coins += 20
                        for _ in range(5):
                            self.coins_anim.append(Coin(
                                self.boss.x + random.randint(-30, 30),
                                self.boss.y + random.randint(-20, 20)))
                        for _ in range(40):
                            self.particles.append(Particle(
                                self.boss.x + random.randint(-30, 30),
                                self.boss.y + random.randint(-30, 30),
                                random.choice([RED, ORANGE, YELLOW, DARK_RED]),
                                random.uniform(-5, 5), random.uniform(-5, 2),
                                random.randint(20, 50), random.randint(3, 7)))
                        self.explosions.append(Explosion(self.boss.x, self.boss.y, 100, 0))

        self.bullets = [b for b in self.bullets if b.alive]

        # 敵弾丸更新
        if self.boss and self.boss.alive:
            self.boss.update(self.enemy_bullets, self.commander, self.soldiers)

        for e in self.enemies:
            if e.alive:
                e.update(self.commander.y, self.enemy_bullets, self.soldiers)

        for eb in self.enemy_bullets:
            eb.update()
            if not eb.alive:
                continue
            # 兵士への当たり判定
            for s in self.soldiers:
                if not s.alive:
                    continue
                dist = math.sqrt((eb.x - s.x)**2 + (eb.y - s.y)**2)
                if dist < 15:
                    s.alive = False
                    eb.alive = False
                    self._spawn_death_particles(s)
                    self.popups.append(DamagePopup(s.x, s.y - 10, "KIA", RED))
                    break
            # 指揮官への当たり判定
            if eb.alive:
                dist = math.sqrt((eb.x - self.commander.x)**2 + (eb.y - self.commander.y)**2)
                if dist < 20:
                    self.commander.take_damage(eb.damage)
                    self.popups.append(DamagePopup(
                        self.commander.x, self.commander.y - 20,
                        eb.damage if self.commander.shield_timer <= 0 else "BLOCK",
                        RED if self.commander.shield_timer <= 0 else CYAN))
                    eb.alive = False

        self.enemy_bullets = [eb for eb in self.enemy_bullets if eb.alive]

        # 敵が指揮官に到達
        for e in self.enemies:
            if e.alive and e.y >= self.commander.y - 20:
                self.commander.take_damage(e.damage)
                e.alive = False
                self.popups.append(DamagePopup(self.commander.x, self.commander.y - 20, e.damage, RED))
                self._spawn_death_particles(e)

        # 死亡チェック
        self.enemies = [e for e in self.enemies if e.alive or e.flash_timer > 0]
        self.soldiers = [s for s in self.soldiers if s.alive]

        # エフェクト更新
        self.particles = [p for p in self.particles if p.update()]
        self.popups = [p for p in self.popups if p.update()]
        self.coins_anim = [c for c in self.coins_anim if c.update()]
        self.explosions = [ex for ex in self.explosions if ex.update()]
        self.portal_effects = [pe for pe in self.portal_effects if pe.update()]

        # ゲームオーバーチェック
        if self.commander.hp <= 0:
            self.state = GameState.GAME_OVER

        # ウェーブ完了チェック
        all_dead = all(not e.alive for e in self.enemies) and len(self.spawn_queue) == 0
        boss_done = self.boss is None or not self.boss.alive
        if all_dead and boss_done and not self.wave_complete:
            self.wave_complete = True
            self.wave_timer = 120  # 次ウェーブまで2秒

        if self.wave_complete:
            self.wave_timer -= 1
            if self.wave_timer <= 0:
                self.current_wave += 1
                if self.current_wave >= len(WAVE_DEFINITIONS):
                    self.state = GameState.GAME_CLEAR
                else:
                    self.boss = None
                    self.start_wave()

    # ── 描画 ──────────────────────────────────────────
    def draw(self):
        self.screen.fill(SKY_DARK)

        if self.state == GameState.TITLE:
            self.draw_title()
            return
        elif self.state == GameState.GAME_OVER:
            self.draw_game_over()
            return
        elif self.state == GameState.GAME_CLEAR:
            self.draw_game_clear()
            return

        # 背景の崩壊した都市
        self.draw_background()
        # 道路
        self.draw_road()
        # エフェクト（下層）
        for ex in self.explosions:
            ex.draw(self.screen)
        for pe in self.portal_effects:
            pe.draw(self.screen)
        # 敵
        for e in self.enemies:
            e.draw(self.screen)
        # ボス
        if self.boss and self.boss.alive:
            self.boss.draw(self.screen)
        # 兵士
        for s in self.soldiers:
            s.draw(self.screen)
        # 指揮官
        self.commander.draw(self.screen)
        # 弾丸
        for b in self.bullets:
            b.draw(self.screen)
        for eb in self.enemy_bullets:
            eb.draw(self.screen)
        # パーティクル
        for p in self.particles:
            p.draw(self.screen)
        # ダメージポップアップ
        for popup in self.popups:
            popup.draw(self.screen, self.font)
        # コインアニメーション
        for c in self.coins_anim:
            c.draw(self.screen, self.font_small)
        # HUD
        self.draw_hud()
        # ウェーブイントロ
        if self.state == GameState.WAVE_INTRO:
            self.draw_wave_intro()
        # ドラッグ中アイテム
        if self.dragging_item is not None:
            self.draw_dragging_item()

    def draw_background(self):
        # 崩壊した都市の建物（左側）
        buildings_left = [
            (20, 100, 60, 500),
            (90, 60, 50, 540),
            (150, 150, 55, 450),
            (50, 200, 70, 400),
        ]
        buildings_right = [
            (670, 80, 55, 520),
            (735, 130, 60, 470),
            (805, 50, 65, 550),
            (700, 180, 50, 420),
        ]
        for bx, by, bw, bh in buildings_left + buildings_right:
            pygame.draw.rect(self.screen, BUILDING_COLOR, (bx, by, bw, bh))
            pygame.draw.rect(self.screen, BUILDING_DARK, (bx + 2, by + 2, bw - 4, bh - 4))
            # 窓
            for wy in range(by + 15, by + bh - 20, 30):
                for wx in range(bx + 8, bx + bw - 12, 18):
                    if random.random() > 0.1:  # 一部の窓は壊れている
                        pygame.draw.rect(self.screen, WINDOW_COLOR, (wx, wy, 10, 12))

        # 瓦礫（道路の外側）
        random.seed(42)
        for _ in range(15):
            rx = random.choice([random.randint(10, ROAD_LEFT - 20), random.randint(ROAD_RIGHT + 10, SCREEN_W - 20)])
            ry = random.randint(100, SCREEN_H - 100)
            rs = random.randint(5, 15)
            pygame.draw.rect(self.screen, GRAY, (rx, ry, rs, rs // 2))
        random.seed()

    def draw_road(self):
        # 道路面
        pygame.draw.rect(self.screen, GRAY, (ROAD_LEFT, 0, ROAD_RIGHT - ROAD_LEFT, SCREEN_H))

        # 道路の端線
        pygame.draw.line(self.screen, WHITE, (ROAD_LEFT, 0), (ROAD_LEFT, SCREEN_H), 3)
        pygame.draw.line(self.screen, WHITE, (ROAD_RIGHT, 0), (ROAD_RIGHT, SCREEN_H), 3)

        # 中央分離帯（黄色ストライプ）
        for y in range(-40 + self.road_offset, SCREEN_H, 40):
            pygame.draw.rect(self.screen, YELLOW, (ROAD_CENTER - 2, y, 4, 20))

        # レーンハイライト（集中先）
        highlight_x = ROAD_LEFT if self.commander.focused_lane == 0 else ROAD_CENTER
        highlight_surf = pygame.Surface((LANE_WIDTH, SCREEN_H), pygame.SRCALPHA)
        highlight_surf.fill((0, 200, 255, 20))
        self.screen.blit(highlight_surf, (highlight_x, 0))

    def draw_hud(self):
        # HUD背景
        hud_surface = pygame.Surface((SCREEN_W, HUD_HEIGHT), pygame.SRCALPHA)
        hud_surface.fill((0, 0, 0, 180))
        self.screen.blit(hud_surface, (0, SCREEN_H - HUD_HEIGHT))

        y_base = SCREEN_H - HUD_HEIGHT + 8

        # HP
        hp_text = self.font.render(f"HP", True, WHITE)
        self.screen.blit(hp_text, (15, y_base))
        bar_x = 45
        bar_w = 120
        bar_h = 16
        pygame.draw.rect(self.screen, DARK_RED, (bar_x, y_base + 2, bar_w, bar_h))
        hp_w = int(bar_w * self.commander.hp / self.commander.max_hp)
        hp_color = GREEN if self.commander.hp > 50 else YELLOW if self.commander.hp > 25 else RED
        pygame.draw.rect(self.screen, hp_color, (bar_x, y_base + 2, hp_w, bar_h))
        hp_num = self.font_small.render(f"{self.commander.hp}/{self.commander.max_hp}", True, WHITE)
        self.screen.blit(hp_num, (bar_x + bar_w // 2 - hp_num.get_width() // 2, y_base + 3))

        # ウェーブ
        wave_text = self.font.render(f"WAVE {self.current_wave + 1}/{len(WAVE_DEFINITIONS)}", True, CYAN)
        self.screen.blit(wave_text, (180, y_base))

        # コイン
        pygame.draw.circle(self.screen, GOLD, (340, y_base + 9), 8)
        pygame.draw.circle(self.screen, YELLOW, (340, y_base + 9), 5)
        coin_text = self.font.render(f"x {self.commander.coins}", True, GOLD)
        self.screen.blit(coin_text, (352, y_base))

        # シールド残り
        if self.commander.shield_timer > 0:
            shield_text = self.font_small.render(
                f"SHIELD: {self.commander.shield_timer // 60 + 1}s", True, CYAN)
            self.screen.blit(shield_text, (180, y_base + 22))

        # 兵士数
        alive_soldiers = sum(1 for s in self.soldiers if s.alive)
        soldier_text = self.font_small.render(f"兵士: {alive_soldiers}", True, GREEN)
        self.screen.blit(soldier_text, (15, y_base + 22))

        # アイテムスロット
        slot_start_x = 440
        for i, item in enumerate(ITEMS):
            sx = slot_start_x + i * (ITEM_SLOT_SIZE + 12)
            sy = SCREEN_H - ITEM_SLOT_SIZE - 15

            # スロット背景
            can_afford = self.commander.coins >= item["cost"]
            bg_color = (40, 40, 50) if can_afford else (25, 25, 30)
            pygame.draw.rect(self.screen, bg_color, (sx, sy, ITEM_SLOT_SIZE, ITEM_SLOT_SIZE), border_radius=6)
            border_color = item["color"] if can_afford else DARK_GRAY
            pygame.draw.rect(self.screen, border_color, (sx, sy, ITEM_SLOT_SIZE, ITEM_SLOT_SIZE), 2, border_radius=6)

            # アイコン
            icon_text = self.font_large.render(item["icon"], True, item["color"] if can_afford else DARK_GRAY)
            self.screen.blit(icon_text, (sx + ITEM_SLOT_SIZE // 2 - icon_text.get_width() // 2,
                                          sy + 4))

            # コスト
            cost_text = self.font_small.render(f"${item['cost']}", True, GOLD if can_afford else DARK_GRAY)
            self.screen.blit(cost_text, (sx + ITEM_SLOT_SIZE // 2 - cost_text.get_width() // 2,
                                          sy + ITEM_SLOT_SIZE - 14))

        # レーン切替ヒント
        hint = self.font_small.render("←→:レーン切替  アイテム:ドラッグ&ドロップ", True, LIGHT_GRAY)
        self.screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 14))

    def draw_dragging_item(self):
        if self.dragging_item is None:
            return
        item = ITEMS[self.dragging_item]
        mx, my = self.drag_pos
        # ドラッグ中のアイテム表示
        pygame.draw.circle(self.screen, item["color"], (mx, my), 20, 3)
        icon = self.font_large.render(item["icon"], True, item["color"])
        self.screen.blit(icon, (mx - icon.get_width() // 2, my - icon.get_height() // 2))

        # レーンハイライト
        if ROAD_LEFT <= mx <= ROAD_CENTER:
            highlight_surf = pygame.Surface((LANE_WIDTH, SCREEN_H), pygame.SRCALPHA)
            highlight_surf.fill((item["color"][0], item["color"][1], item["color"][2], 30))
            self.screen.blit(highlight_surf, (ROAD_LEFT, 0))
        elif ROAD_CENTER < mx <= ROAD_RIGHT:
            highlight_surf = pygame.Surface((LANE_WIDTH, SCREEN_H), pygame.SRCALPHA)
            highlight_surf.fill((item["color"][0], item["color"][1], item["color"][2], 30))
            self.screen.blit(highlight_surf, (ROAD_CENTER, 0))

    def draw_wave_intro(self):
        wave = WAVE_DEFINITIONS[self.current_wave]
        # 暗転
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        alpha = int(150 * (self.wave_intro_timer / 120))
        overlay.fill((0, 0, 0, alpha))
        self.screen.blit(overlay, (0, 0))

        # テキスト
        msg = wave["message"]
        text = self.font_large.render(msg, True, RED if wave.get("boss") else CYAN)
        self.screen.blit(text, (SCREEN_W // 2 - text.get_width() // 2, SCREEN_H // 2 - 30))

        if wave.get("boss"):
            boss_text = self.font.render("巨大な敵が接近中...", True, ORANGE)
            self.screen.blit(boss_text, (SCREEN_W // 2 - boss_text.get_width() // 2, SCREEN_H // 2 + 20))

    def draw_title(self):
        self.screen.fill(SKY_DARK)
        self.draw_background()
        self.draw_road()

        # タイトルオーバーレイ
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        # タイトル
        title1 = self.font_title.render("ツイン・ロード・サバイバル", True, CYAN)
        title2 = self.font_large.render("ラスト・ディフェンス", True, ORANGE)

        self.screen.blit(title1, (SCREEN_W // 2 - title1.get_width() // 2, 200))
        self.screen.blit(title2, (SCREEN_W // 2 - title2.get_width() // 2, 270))

        # 点滅テキスト
        if pygame.time.get_ticks() % 1000 < 700:
            start = self.font.render("PRESS SPACE OR CLICK TO START", True, WHITE)
            self.screen.blit(start, (SCREEN_W // 2 - start.get_width() // 2, 400))

        # 操作説明
        controls = [
            "← → : レーン切り替え（火力集中先）",
            "アイテムをドラッグ＆ドロップでレーンに配置",
            "兵士は射程内の敵を自動攻撃します",
        ]
        for i, text in enumerate(controls):
            t = self.font_small.render(text, True, LIGHT_GRAY)
            self.screen.blit(t, (SCREEN_W // 2 - t.get_width() // 2, 460 + i * 24))

    def draw_game_over(self):
        self.draw()  # 背景描画（再帰防止のため直接呼ばない）
        # 実際には update されないので背景は止まっている

        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((100, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        text = self.font_title.render("GAME OVER", True, RED)
        self.screen.blit(text, (SCREEN_W // 2 - text.get_width() // 2, 250))

        wave_text = self.font_large.render(f"到達 WAVE: {self.current_wave + 1}", True, WHITE)
        self.screen.blit(wave_text, (SCREEN_W // 2 - wave_text.get_width() // 2, 330))

        if pygame.time.get_ticks() % 1000 < 700:
            retry = self.font.render("PRESS R TO RETRY / PRESS Q TO QUIT", True, WHITE)
            self.screen.blit(retry, (SCREEN_W // 2 - retry.get_width() // 2, 420))

    def draw_game_clear(self):
        self.screen.fill(SKY_DARK)
        self.draw_background()
        self.draw_road()

        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 50, 0, 150))
        self.screen.blit(overlay, (0, 0))

        text = self.font_title.render("MISSION COMPLETE!", True, GOLD)
        self.screen.blit(text, (SCREEN_W // 2 - text.get_width() // 2, 220))

        sub = self.font_large.render("全ウェーブを撃退した！", True, CYAN)
        self.screen.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, 300))

        coins_text = self.font.render(f"獲得コイン: {self.commander.coins}", True, GOLD)
        self.screen.blit(coins_text, (SCREEN_W // 2 - coins_text.get_width() // 2, 370))

        if pygame.time.get_ticks() % 1000 < 700:
            retry = self.font.render("PRESS R TO REPLAY / PRESS Q TO QUIT", True, WHITE)
            self.screen.blit(retry, (SCREEN_W // 2 - retry.get_width() // 2, 440))

    # ── イベント処理 ──────────────────────────────────
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if self.state == GameState.TITLE:
                    if event.key == pygame.K_SPACE:
                        self.start_wave()
                elif self.state == GameState.PLAYING or self.state == GameState.WAVE_INTRO:
                    if event.key == pygame.K_LEFT:
                        self.commander.focused_lane = 0
                    elif event.key == pygame.K_RIGHT:
                        self.commander.focused_lane = 1
                elif self.state in (GameState.GAME_OVER, GameState.GAME_CLEAR):
                    if event.key == pygame.K_r:
                        self.reset()
                        self.start_wave()
                    elif event.key == pygame.K_q:
                        return False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                if self.state == GameState.TITLE:
                    self.start_wave()

                elif self.state == GameState.PLAYING:
                    # アイテムスロットのクリック → ドラッグ開始
                    slot_start_x = 440
                    for i in range(len(ITEMS)):
                        sx = slot_start_x + i * (ITEM_SLOT_SIZE + 12)
                        sy = SCREEN_H - ITEM_SLOT_SIZE - 15
                        if sx <= mx <= sx + ITEM_SLOT_SIZE and sy <= my <= sy + ITEM_SLOT_SIZE:
                            if self.commander.coins >= ITEMS[i]["cost"]:
                                self.dragging_item = i
                                self.drag_pos = (mx, my)
                            break
                    else:
                        # レーンクリックで集中切替
                        if ROAD_LEFT <= mx <= ROAD_CENTER:
                            self.commander.focused_lane = 0
                        elif ROAD_CENTER < mx <= ROAD_RIGHT:
                            self.commander.focused_lane = 1

            if event.type == pygame.MOUSEMOTION:
                if self.dragging_item is not None:
                    self.drag_pos = event.pos

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.dragging_item is not None:
                    mx, my = event.pos
                    # ドロップ先判定
                    if ROAD_LEFT <= mx <= ROAD_CENTER:
                        self.use_item(self.dragging_item, 0)
                    elif ROAD_CENTER < mx <= ROAD_RIGHT:
                        self.use_item(self.dragging_item, 1)
                    self.dragging_item = None

        return True

    # ── メインループ ──────────────────────────────────
    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()

            # draw_game_over/clear は特殊なのでここで分岐
            if self.state == GameState.GAME_OVER:
                self.screen.fill(SKY_DARK)
                self.draw_background()
                self.draw_road()
                for e in self.enemies:
                    e.draw(self.screen)
                if self.boss and self.boss.alive:
                    self.boss.draw(self.screen)
                for s in self.soldiers:
                    s.draw(self.screen)
                self.commander.draw(self.screen)
                self.draw_hud()
                # オーバーレイ
                overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                overlay.fill((100, 0, 0, 150))
                self.screen.blit(overlay, (0, 0))
                text = self.font_title.render("GAME OVER", True, RED)
                self.screen.blit(text, (SCREEN_W // 2 - text.get_width() // 2, 250))
                wave_text = self.font_large.render(f"到達 WAVE: {self.current_wave + 1}", True, WHITE)
                self.screen.blit(wave_text, (SCREEN_W // 2 - wave_text.get_width() // 2, 330))
                if pygame.time.get_ticks() % 1000 < 700:
                    retry = self.font.render("PRESS R TO RETRY / PRESS Q TO QUIT", True, WHITE)
                    self.screen.blit(retry, (SCREEN_W // 2 - retry.get_width() // 2, 420))
            elif self.state == GameState.GAME_CLEAR:
                self.screen.fill(SKY_DARK)
                self.draw_background()
                self.draw_road()
                overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                overlay.fill((0, 50, 0, 150))
                self.screen.blit(overlay, (0, 0))
                text = self.font_title.render("MISSION COMPLETE!", True, GOLD)
                self.screen.blit(text, (SCREEN_W // 2 - text.get_width() // 2, 220))
                sub = self.font_large.render("全ウェーブを撃退した！", True, CYAN)
                self.screen.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, 300))
                coins_text = self.font.render(f"獲得コイン: {self.commander.coins}", True, GOLD)
                self.screen.blit(coins_text, (SCREEN_W // 2 - coins_text.get_width() // 2, 370))
                if pygame.time.get_ticks() % 1000 < 700:
                    retry = self.font.render("PRESS R TO REPLAY / PRESS Q TO QUIT", True, WHITE)
                    self.screen.blit(retry, (SCREEN_W // 2 - retry.get_width() // 2, 440))
            else:
                self.draw()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
