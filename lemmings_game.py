#!/usr/bin/env python3
"""
Pygame Lemmings Ultimate Edition
=================================
A classic Lemmings-style puzzle game with 15 levels, level editor, and many features.

Controls:
  1-8          Select skill          Left Click   Assign skill
  Right Click  Deselect              P / Space    Pause
  N            Nuke all              R            Restart
  +/-          Release rate          F            Fast-forward (1x/2x/3x)
  Arrow keys   Scroll camera         M            Toggle minimap
  Z            Zoom (1x/0.5x)        C            Auto-camera follow
  E            Level Editor          Esc          Menu / Quit

Requirements:  pip install pygame
"""
import pygame, sys, random, math, struct, io, wave, json, base64, os

# ── constants ────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1024, 700
GAME_W, GAME_H = 800, 600
UI_X = GAME_W
UI_W = SCREEN_W - GAME_W

FPS = 60
GRAVITY = 0.5
WALK_SPEED = 1
CLIMB_SPEED = 1

AIR, SOLID, STEEL, WATER, FIRE, SPIKE, TRAMPOLINE = 0, 1, 2, 3, 4, 5, 6
ONEWAY_L, ONEWAY_R = 7, 8

COL_SKY_TOP = (30, 30, 70)
COL_SKY_BOT = (90, 130, 190)
COL_DIRT = [(120, 80, 40), (100, 68, 32), (108, 74, 36), (130, 86, 44)]
COL_GRASS = [(50, 160, 50), (30, 130, 30)]
COL_STEEL = (160, 160, 175)
COL_STONE = [(130, 130, 140), (110, 110, 120)]
COL_WATER_TOP = (40, 100, 220)
COL_WATER_DEEP = (20, 60, 150)
COL_FIRE = [(255, 120, 20), (255, 60, 10), (255, 200, 50)]
COL_SPIKE = (180, 180, 190)
COL_TRAMPOLINE = (255, 200, 0)
COL_ONEWAY = (200, 200, 60)

COL_LC = (0, 230, 0)
COL_LB = (90, 90, 240)
COL_LR = (255, 200, 150)
COL_LH = (180, 120, 60)
COL_EXIT = (220, 40, 40)
COL_ENTRANCE = (50, 200, 50)
COL_UI_BG = (40, 42, 60)
COL_UI_BORDER = (90, 90, 130)
COL_UI_TEXT = (215, 215, 235)
COL_UI_HL = (255, 255, 100)
COL_UI_SK = (60, 62, 88)
COL_UI_SK_SEL = (90, 120, 190)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GOLD = (255, 215, 0)
SILVER = (192, 192, 192)
BRONZE = (205, 127, 50)
COL_PICKUP = (255, 100, 255)
COL_TREE_TRUNK = (100, 65, 30)
COL_TREE_LEAF = [(30, 140, 30), (40, 160, 40), (25, 120, 25)]
COL_ROCK = [(140, 140, 150), (120, 120, 130), (160, 160, 170)]
COL_FLOWER = [(255, 80, 80), (255, 200, 50), (200, 100, 255), (255, 150, 200)]

def _script_dir():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()

SCORES_FILE = os.path.join(_script_dir(), "lemmings_scores.json")
LEVELS_DIR = os.path.join(_script_dir(), "levels")

def load_scores():
    try:
        with open(SCORES_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_scores(scores):
    try:
        with open(SCORES_FILE, 'w') as f:
            json.dump(scores, f)
    except Exception:
        pass

class Skill:
    NONE = 0; BLOCKER = 1; CLIMBER = 2; FLOATER = 3; BOMBER = 4
    BUILDER = 5; BASHER = 6; MINER = 7; DIGGER = 8

SKILL_NAMES = {
    Skill.NONE:"None", Skill.BLOCKER:"Blocker", Skill.CLIMBER:"Climber",
    Skill.FLOATER:"Floater", Skill.BOMBER:"Bomber", Skill.BUILDER:"Builder",
    Skill.BASHER:"Basher", Skill.MINER:"Miner", Skill.DIGGER:"Digger",
}
SKILL_KEYS = {
    pygame.K_1:Skill.BLOCKER, pygame.K_2:Skill.CLIMBER, pygame.K_3:Skill.FLOATER,
    pygame.K_4:Skill.BOMBER, pygame.K_5:Skill.BUILDER, pygame.K_6:Skill.BASHER,
    pygame.K_7:Skill.MINER, pygame.K_8:Skill.DIGGER,
}
SKILL_HOTKEYS = {
    Skill.BLOCKER:"1", Skill.CLIMBER:"2", Skill.FLOATER:"3", Skill.BOMBER:"4",
    Skill.BUILDER:"5", Skill.BASHER:"6", Skill.MINER:"7", Skill.DIGGER:"8",
}

class LState:
    WALKING=0; FALLING=1; SPLATTING=2; BLOCKING=3; CLIMBING=4
    FLOATING=5; BUILDING=6; BASHING=7; MINING=8; DIGGING=9
    EXITING=10; DEAD=11; EXPLODING=12; DROWNING=13; BURNING=14
    PICKING_UP=15

def _make_wav(samples, sr=22050):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        data = b"".join(struct.pack("<h", max(-32767, min(32767, int(s * 32767)))) for s in samples)
        w.writeframes(data)
    buf.seek(0)
    return pygame.mixer.Sound(buf)

def _gen_sounds():
    sr = 22050
    sounds = {}
    n = int(sr * 0.08)
    sounds["click"] = _make_wav([0.3 * math.sin(2 * math.pi * 800 * i / sr) * (1 - i / n) for i in range(n)], sr)
    n = int(sr * 0.15)
    sounds["splat"] = _make_wav([random.uniform(-0.4, 0.4) * (1 - i / n) for i in range(n)], sr)
    n = int(sr * 0.4)
    sounds["boom"] = _make_wav([random.uniform(-0.6, 0.6) * (1 - i / n) ** 0.5 for i in range(n)], sr)
    n = int(sr * 0.05)
    sounds["dig"] = _make_wav([random.uniform(-0.15, 0.15) * (1 - i / n) for i in range(n)], sr)
    n = int(sr * 0.2)
    sounds["ding"] = _make_wav([0.25 * math.sin(2 * math.pi * 1200 * i / sr) * (1 - i / n) for i in range(n)], sr)
    n = int(sr * 0.8)
    t = [i / sr for i in range(n)]; s = []
    for ti in t:
        note = 523 if ti < 0.2 else (659 if ti < 0.4 else (784 if ti < 0.6 else 1047))
        env = max(0, 1 - (ti % 0.2) * 5)
        s.append(0.2 * math.sin(2 * math.pi * note * ti) * env)
    sounds["fanfare"] = _make_wav(s, sr)
    n = int(sr * 0.3)
    sounds["splash"] = _make_wav([random.uniform(-0.3, 0.3) * math.sin(2 * math.pi * 200 * i / n) * (1 - i / n) for i in range(n)], sr)
    n = int(sr * 0.2)
    sounds["burn"] = _make_wav([random.uniform(-0.35, 0.35) * (1 - i / n) ** 0.7 for i in range(n)], sr)
    n = int(sr * 0.8)
    sounds["nuke"] = _make_wav([random.uniform(-0.5, 0.5) * (1 - i / n) ** 0.3 for i in range(n)], sr)
    n = int(sr * 0.12)
    sounds["bounce"] = _make_wav([0.3 * math.sin(2 * math.pi * (400 + 600 * i / n) * i / sr) * (1 - i / n) for i in range(n)], sr)
    n = int(sr * 0.1)
    sounds["pickup"] = _make_wav([0.3 * math.sin(2*math.pi*(800+400*i/n)*i/sr)*(1-i/n) for i in range(n)], sr)
    n = int(sr * 0.06)
    sounds["step"] = _make_wav([random.uniform(-0.05, 0.05) * (1 - i / n) for i in range(n)], sr)
    n = int(sr * 0.15)
    sounds["build_place"] = _make_wav([0.2 * math.sin(2*math.pi*600*i/sr)*(1-i/n) for i in range(n)], sr)
    n = int(sr * 0.25)
    sounds["warning"] = _make_wav([0.3*math.sin(2*math.pi*440*i/sr)*(1 if (i//int(sr*0.05))%2==0 else 0) for i in range(n)], sr)
    return sounds


LEVEL_DESCS = {
    1: "Just Dig - Simple intro",
    2: "Bridge the Gap - Builder puzzle",
    3: "Climb High - Vertical with fire",
    4: "Steel Maze - Indestructible walls",
    5: "The Gauntlet - Traps everywhere",
    6: "Random Hills - Procedural",
    7: "Trampoline Park - Bounce up!",
    8: "The Tower - Climb to the top",
    9: "The Cave - Underground caverns",
    10: "Island Hopping - Water below",
    11: "Lava Fields - Fire everywhere",
    12: "Ice Castle - Steel fortress",
    13: "Maze Runner - Find the path",
    14: "Pitfall - Deadly traps",
    15: "Grand Finale - Ultimate challenge",
}

PICKUP_TYPES = ["builder", "bomber", "digger", "basher", "miner", "floater", "climber", "blocker"]

def create_level(num):
    W, H = 1600, 1200
    terrain = bytearray(W * H)
    entrance = exit_pos = None
    pickups = []
    save_count = 10; total_count = 20; release_rate = 35
    time_limit = 300
    sc = {Skill.BLOCKER:5, Skill.CLIMBER:5, Skill.FLOATER:5, Skill.BOMBER:5,
          Skill.BUILDER:10, Skill.BASHER:5, Skill.MINER:5, Skill.DIGGER:5}

    def set_t(x, y, v=SOLID):
        if 0 <= x < W and 0 <= y < H:
            terrain[y * W + x] = v

    def fill(x1, y1, x2, y2, v=SOLID):
        for y in range(max(0, y1), min(H, y2)):
            for x in range(max(0, x1), min(W, x2)):
                set_t(x, y, v)

    def fill_steel(x1, y1, x2, y2):
        fill(x1, y1, x2, y2, STEEL)

    def add_water(x1, y1, x2, y2):
        for y in range(max(0, y1), min(H, y2)):
            for x in range(max(0, x1), min(W, x2)):
                if terrain[y * W + x] == AIR:
                    terrain[y * W + x] = WATER

    def add_fire(x1, y1, x2, y2):
        for y in range(max(0, y1), min(H, y2)):
            for x in range(max(0, x1), min(W, x2)):
                if terrain[y * W + x] == AIR:
                    terrain[y * W + x] = FIRE

    def add_spikes(x1, y1, x2, y2):
        for y in range(max(0, y1), min(H, y2)):
            for x in range(max(0, x1), min(W, x2)):
                if terrain[y * W + x] == AIR:
                    terrain[y * W + x] = SPIKE

    def add_trampoline(x1, y1, x2, y2):
        for y in range(max(0, y1), min(H, y2)):
            for x in range(max(0, x1), min(W, x2)):
                if terrain[y * W + x] == AIR:
                    terrain[y * W + x] = TRAMPOLINE

    def add_oneway(x1, y1, x2, y2, d=ONEWAY_R):
        for y in range(max(0, y1), min(H, y2)):
            for x in range(max(0, x1), min(W, x2)):
                if terrain[y * W + x] == AIR:
                    terrain[y * W + x] = d

    def add_pickup(x, y, pt):
        if 0 <= x < W and 0 <= y < H:
            pickups.append({"x": x, "y": y, "type": pt, "collected": False})

    if num == 1:
        total_count = 20; save_count = 10; release_rate = 40; time_limit = 300
        fill(0, 900, W, H); fill(0, 898, W, 904); fill_steel(0, 895, W, 898)
        fill(750, 650, 800, 900); fill(1100, 700, 1200, 900); fill(1200, 750, W, 904)
        entrance = (200, 870); exit_pos = (1400, 720)
        sc = {Skill.BLOCKER:2, Skill.CLIMBER:2, Skill.FLOATER:5, Skill.BOMBER:5,
              Skill.BUILDER:8, Skill.BASHER:3, Skill.MINER:3, Skill.DIGGER:10}

    elif num == 2:
        total_count = 20; save_count = 12; release_rate = 35; time_limit = 300
        fill(0, 900, 500, H); fill(700, 900, W, H)
        fill(0, 898, 500, 904); fill(700, 898, W, 904)
        add_water(500, 960, 700, H)
        fill_steel(500, 955, 510, H); fill_steel(690, 955, 700, H)
        fill_steel(0, 895, 500, 898); fill_steel(700, 895, W, 898)
        entrance = (150, 870); exit_pos = (1300, 870)
        sc = {Skill.BLOCKER:3, Skill.CLIMBER:3, Skill.FLOATER:5, Skill.BOMBER:3,
              Skill.BUILDER:15, Skill.BASHER:3, Skill.MINER:3, Skill.DIGGER:3}

    elif num == 3:
        total_count = 20; save_count = 12; release_rate = 30; time_limit = 360
        fill(0, 1050, W, H); fill(0, 1048, W, 1054); fill_steel(0, 1045, W, 1048)
        fill(100, 900, 500, 908); fill(600, 750, 1000, 758)
        fill(200, 600, 600, 608); fill(800, 450, 1200, 458); fill(400, 300, 800, 308)
        add_fire(480, 890, 520, 898); add_fire(580, 740, 620, 748); add_fire(180, 590, 220, 598)
        fill(550, 750, 560, 908); fill(700, 600, 710, 758); fill(300, 450, 310, 608)
        fill(900, 250, 1000, 258)
        entrance = (150, 870); exit_pos = (950, 225)
        sc = {Skill.BLOCKER:4, Skill.CLIMBER:10, Skill.FLOATER:8, Skill.BOMBER:3,
              Skill.BUILDER:8, Skill.BASHER:5, Skill.MINER:3, Skill.DIGGER:3}

    elif num == 4:
        total_count = 25; save_count = 15; release_rate = 30; time_limit = 420
        fill(0, 950, W, H); fill(0, 948, W, 954); fill_steel(0, 945, W, 948)
        fill(300, 600, 320, 948); fill_steel(300, 590, 320, 600)
        fill(600, 700, 620, 948); fill_steel(600, 690, 620, 700)
        fill(900, 550, 920, 948); fill_steel(900, 540, 920, 550)
        for ry in range(948, H):
            for rx in range(310, 600):
                if 0 <= rx < W and 0 <= ry < H: terrain[ry * W + rx] = AIR
            for rx in range(610, 900):
                if 0 <= rx < W and 0 <= ry < H: terrain[ry * W + rx] = AIR
        fill(400, 750, 600, 758); fill(700, 650, 900, 658)
        add_water(310, 1000, 600, H); add_spikes(610, 1000, 900, H)
        entrance = (100, 920); exit_pos = (1350, 920)
        sc = {Skill.BLOCKER:5, Skill.CLIMBER:5, Skill.FLOATER:8, Skill.BOMBER:5,
              Skill.BUILDER:8, Skill.BASHER:10, Skill.MINER:10, Skill.DIGGER:8}

    elif num == 5:
        total_count = 30; save_count = 18; release_rate = 25; time_limit = 480
        fill(0, 950, W, H); fill(0, 948, W, 954); fill_steel(0, 945, W, 948)
        fill(200, 850, 600, 858); fill(800, 800, 1200, 808)
        fill(400, 700, 800, 708); fill(1000, 600, 1400, 608); fill(600, 500, 1000, 508)
        for ry in range(948, H):
            for rx in range(0, 200):
                if 0 <= rx < W and 0 <= ry < H: terrain[ry * W + rx] = AIR
        add_water(0, 1000, 200, H)
        add_fire(600, 840, 640, 848); add_spikes(800, 790, 840, 798)
        add_water(400, 690, 440, 698); add_fire(1000, 590, 1040, 598)
        fill(700, 600, 710, 808); fill(500, 500, 510, 708); fill(1100, 500, 1110, 608)
        fill_steel(300, 850, 310, 948); fill_steel(900, 800, 910, 948)
        entrance = (100, 920); exit_pos = (750, 470)
        sc = {Skill.BLOCKER:6, Skill.CLIMBER:10, Skill.FLOATER:10, Skill.BOMBER:8,
              Skill.BUILDER:12, Skill.BASHER:8, Skill.MINER:8, Skill.DIGGER:8}

    elif num == 6:
        total_count = 20; save_count = 12; release_rate = 35; time_limit = 300
        for x in range(W):
            h = int(800 + 80*math.sin(x*0.008) + 50*math.sin(x*0.02) + 30*math.sin(x*0.04))
            for y in range(h, H): set_t(x, y)
            set_t(x, h); set_t(x, h - 1)
        for _ in range(6):
            wx = random.randint(400, W-400); wy = random.randint(400, 850)
            fill(wx, wy, wx + random.randint(15,25), 950)
        for _ in range(3):
            hx = random.randint(300, W-300); hy = random.randint(850, 1000)
            hw = random.randint(60, 120)
            if random.random() < 0.5: add_water(hx, hy, hx+hw, hy+40)
            else: add_fire(hx, hy-20, hx+hw, hy)
        entrance = (150, 780); exit_pos = (W-200, 780)

    elif num == 7:
        total_count = 25; save_count = 15; release_rate = 35; time_limit = 360
        fill(0, 1050, W, H); fill(0, 1048, W, 1054); fill_steel(0, 1045, W, 1048)
        fill(100, 850, 500, 858); fill_steel(100, 848, 500, 850)
        fill(600, 700, 1100, 708); fill_steel(600, 698, 1100, 700)
        fill(200, 550, 700, 558); fill_steel(200, 548, 700, 550)
        fill(900, 350, 1300, 358); fill_steel(900, 348, 1300, 350)
        add_trampoline(300, 1045, 420, 1048); add_trampoline(800, 695, 950, 698)
        add_trampoline(350, 545, 550, 548); add_trampoline(1000, 345, 1200, 348)
        add_water(520, 1060, 580, H); add_water(1100, 1060, 1160, H)
        add_fire(450, 842, 480, 848); add_fire(1000, 692, 1030, 698)
        entrance = (200, 1020); exit_pos = (1100, 320)
        sc = {Skill.BLOCKER:4, Skill.CLIMBER:6, Skill.FLOATER:8, Skill.BOMBER:5,
              Skill.BUILDER:10, Skill.BASHER:5, Skill.MINER:5, Skill.DIGGER:3}

    elif num == 8:
        total_count = 20; save_count = 12; release_rate = 30; time_limit = 420
        fill(650, 200, 950, H); fill(700, 250, 900, H)
        fill(700, 950, 900, 958); fill(700, 800, 900, 808)
        fill(700, 650, 900, 658); fill(700, 500, 900, 508)
        fill(700, 350, 900, 358); fill(700, 200, 900, 208)
        fill_steel(700, 198, 900, 200)
        add_fire(840, 942, 880, 950); add_fire(840, 792, 880, 800)
        add_fire(840, 642, 880, 650); add_fire(840, 492, 880, 500)
        fill(690, 1000, 700, 1040, AIR); fill(900, 1000, 910, 1040, AIR)
        fill(0, 1050, 650, H); fill(950, 1050, W, H)
        fill(0, 1048, 650, 1054); fill(950, 1048, W, 1054)
        add_water(650, 1060, 950, H)
        entrance = (300, 1020); exit_pos = (800, 170)
        sc = {Skill.BLOCKER:3, Skill.CLIMBER:10, Skill.FLOATER:8, Skill.BOMBER:4,
              Skill.BUILDER:15, Skill.BASHER:3, Skill.MINER:3, Skill.DIGGER:5}

    elif num == 9:
        total_count = 25; save_count = 15; release_rate = 30; time_limit = 480
        fill(0, 1000, W, H); fill(0, 998, W, 1004); fill_steel(0, 995, W, 998)
        fill(0, 0, W, 100); fill_steel(0, 100, W, 104)
        for sx in range(50, W-50, 120):
            sh = random.randint(30, 80)
            fill(sx, 104, sx + 15, 104 + sh)
        fill(100, 800, 450, 808); fill(500, 700, 900, 708)
        fill(950, 600, 1350, 608); fill(200, 500, 600, 508)
        fill(700, 400, 1100, 408); fill(1100, 300, 1500, 308)
        add_water(50, 1010, 200, H); add_water(600, 1010, 800, H); add_water(1200, 1010, 1400, H)
        add_fire(250, 790, 290, 798); add_fire(650, 690, 690, 698); add_fire(1050, 590, 1090, 598)
        fill_steel(450, 600, 460, 808); fill_steel(900, 500, 910, 708); fill_steel(600, 300, 610, 508)
        add_pickup(300, 770, "floater"); add_pickup(700, 670, "builder")
        add_pickup(1100, 570, "bomber"); add_pickup(400, 470, "climber")
        entrance = (200, 970); exit_pos = (1300, 270)
        sc = {Skill.BLOCKER:5, Skill.CLIMBER:8, Skill.FLOATER:6, Skill.BOMBER:5,
              Skill.BUILDER:10, Skill.BASHER:6, Skill.MINER:5, Skill.DIGGER:5}

    elif num == 10:
        total_count = 20; save_count = 12; release_rate = 35; time_limit = 360
        fill(0, 1100, W, H); add_water(0, 950, W, H)
        fill(50, 900, 200, 910); fill(350, 870, 480, 880)
        fill(650, 840, 800, 850); fill(1000, 810, 1150, 820)
        fill(1300, 780, 1450, 790); fill(200, 750, 350, 760)
        fill(550, 720, 700, 730); fill(900, 690, 1050, 700)
        fill(1200, 660, 1350, 670)
        fill_steel(50, 910, 200, 915); fill_steel(350, 880, 480, 885)
        fill_steel(650, 850, 800, 855); fill_steel(1000, 820, 1150, 825)
        fill_steel(1300, 790, 1450, 795)
        add_spikes(420, 860, 450, 870); add_spikes(720, 710, 750, 720)
        add_trampoline(160, 895, 190, 900); add_trampoline(760, 835, 790, 840)
        add_pickup(400, 840, "builder"); add_pickup(750, 690, "builder")
        add_pickup(1100, 660, "floater")
        entrance = (120, 870); exit_pos = (1280, 750)
        sc = {Skill.BLOCKER:3, Skill.CLIMBER:5, Skill.FLOATER:8, Skill.BOMBER:3,
              Skill.BUILDER:12, Skill.BASHER:3, Skill.MINER:2, Skill.DIGGER:2}

    elif num == 11:
        total_count = 30; save_count = 18; release_rate = 25; time_limit = 420
        fill(0, 1000, W, H); fill(0, 998, W, 1004); fill_steel(0, 995, W, 998)
        add_fire(300, 998, 350, H); add_fire(600, 998, 650, H)
        add_fire(900, 998, 950, H); add_fire(1200, 998, 1250, H)
        fill(0, 900, 300, 908); fill(350, 850, 600, 858)
        fill(650, 800, 900, 808); fill(950, 750, 1200, 758); fill(1250, 700, W, 708)
        fill(200, 600, 500, 608); fill(600, 500, 900, 508)
        fill(1000, 400, 1300, 408); fill(700, 300, 1000, 308)
        add_fire(400, 898, 430, 908); add_fire(700, 798, 730, 808)
        add_fire(1050, 748, 1080, 758); add_fire(300, 598, 330, 608); add_fire(750, 498, 780, 508)
        fill(300, 600, 310, 858); fill_steel(300, 590, 310, 600)
        fill(650, 500, 660, 808); fill_steel(650, 490, 660, 500)
        fill(1000, 400, 1010, 758); fill_steel(1000, 390, 1010, 400)
        add_oneway(150, 895, 280, 900, ONEWAY_R); add_oneway(400, 845, 580, 850, ONEWAY_R)
        add_pickup(450, 820, "floater"); add_pickup(800, 770, "builder")
        add_pickup(1100, 720, "climber"); add_pickup(400, 570, "bomber")
        entrance = (100, 870); exit_pos = (850, 270)
        sc = {Skill.BLOCKER:5, Skill.CLIMBER:10, Skill.FLOATER:10, Skill.BOMBER:8,
              Skill.BUILDER:12, Skill.BASHER:6, Skill.MINER:6, Skill.DIGGER:4}

    elif num == 12:
        total_count = 25; save_count = 15; release_rate = 28; time_limit = 480
        fill(0, 1050, W, H); fill(0, 1048, W, 1054); fill_steel(0, 1045, W, 1048)
        fill_steel(0, 200, 30, 1050); fill_steel(W-30, 200, W, 1050); fill_steel(0, 200, W, 230)
        fill_steel(400, 400, 420, 1050); fill_steel(800, 300, 820, 700); fill_steel(1200, 500, 1220, 1050)
        fill(400, 700, 420, 750, AIR); fill(800, 500, 820, 550, AIR); fill(1200, 800, 1220, 850, AIR)
        fill(30, 900, 400, 908); fill(420, 800, 800, 808)
        fill(820, 700, 1200, 708); fill(1220, 600, W-30, 608)
        fill(30, 500, 400, 508); fill(420, 400, 800, 408)
        fill(820, 300, W-30, 308)
        add_water(200, 910, 350, H); add_spikes(600, 810, 750, 820)
        add_fire(1000, 710, 1100, 720); add_water(1300, 610, 1450, H)
        add_spikes(100, 510, 250, 520); add_fire(300, 510, 380, 520)
        add_pickup(200, 870, "climber"); add_pickup(600, 770, "basher")
        add_pickup(1000, 670, "miner"); add_pickup(200, 470, "builder")
        entrance = (150, 870); exit_pos = (1400, 270)
        sc = {Skill.BLOCKER:5, Skill.CLIMBER:8, Skill.FLOATER:8, Skill.BOMBER:6,
              Skill.BUILDER:10, Skill.BASHER:10, Skill.MINER:8, Skill.DIGGER:6}

    elif num == 13:
        total_count = 20; save_count = 10; release_rate = 30; time_limit = 540
        fill(0, 1000, W, H); fill(0, 998, W, 1004); fill_steel(0, 995, W, 998)
        fill_steel(0, 300, W, 310); fill_steel(0, 300, 30, 1000); fill_steel(W-30, 300, W, 1000)
        fill_steel(200, 300, 220, 700); fill_steel(200, 700, 500, 720)
        fill_steel(400, 500, 420, 700); fill_steel(400, 500, 700, 520)
        fill_steel(600, 300, 620, 520); fill_steel(600, 600, 620, 800)
        fill_steel(200, 800, 600, 820)
        fill_steel(800, 300, 820, 600); fill_steel(800, 600, 1100, 620)
        fill_steel(1000, 400, 1020, 620); fill_steel(1000, 400, 1300, 420)
        fill_steel(1200, 300, 1220, 420); fill_steel(1200, 500, 1220, 800)
        fill_steel(800, 800, 1200, 820); fill_steel(1400, 300, 1420, 600)
        fill(200, 600, 220, 650, AIR); fill(400, 600, 420, 650, AIR)
        fill(600, 400, 620, 450, AIR); fill(800, 450, 820, 500, AIR)
        fill(1000, 500, 1020, 550, AIR); fill(1200, 350, 1220, 400, AIR)
        fill(1200, 600, 1220, 650, AIR); fill(1400, 400, 1420, 450, AIR)
        fill(30, 950, W-30, 958)
        add_water(50, 960, 180, H); add_fire(230, 730, 390, 800)
        add_spikes(430, 730, 580, 800); add_water(630, 830, 780, H)
        add_fire(830, 630, 980, 800); add_spikes(1030, 430, 1180, 500); add_water(1230, 830, 1380, H)
        add_pickup(100, 920, "basher"); add_pickup(500, 470, "bomber")
        add_pickup(900, 420, "digger"); add_pickup(1300, 370, "builder")
        entrance = (100, 920); exit_pos = (1450, 320)
        sc = {Skill.BLOCKER:4, Skill.CLIMBER:5, Skill.FLOATER:5, Skill.BOMBER:8,
              Skill.BUILDER:10, Skill.BASHER:12, Skill.MINER:8, Skill.DIGGER:8}

    elif num == 14:
        total_count = 30; save_count = 20; release_rate = 20; time_limit = 360
        fill(0, 950, W, H); fill(0, 948, W, 954); fill_steel(0, 945, W, 948)
        fill(0, 850, 200, 858); add_water(200, 960, 320, H)
        fill_steel(200, 955, 205, H); fill_steel(315, 955, 320, H)
        fill(320, 850, 500, 858); add_spikes(500, 960, 620, 1000)
        fill(620, 850, 800, 858); add_fire(800, 940, 920, 958)
        fill(920, 850, 1100, 858); add_water(1100, 960, 1200, H)
        fill(1200, 850, 1350, 858); add_spikes(1350, 960, 1450, 1000)
        fill(1450, 850, W, 858)
        fill(300, 650, 600, 658); fill(700, 500, 1000, 508); fill(1100, 400, 1400, 408)
        fill_steel(300, 648, 600, 650); fill_steel(700, 498, 1000, 500)
        add_fire(500, 640, 560, 650); add_spikes(900, 490, 960, 500)
        fill(550, 658, 560, 858); fill(950, 508, 960, 708)
        fill_steel(550, 648, 560, 658); fill_steel(950, 498, 960, 508)
        add_trampoline(150, 845, 180, 850); add_trampoline(1250, 845, 1280, 850)
        add_pickup(400, 620, "climber"); add_pickup(800, 470, "floater"); add_pickup(1200, 370, "builder")
        entrance = (100, 820); exit_pos = (1500, 820)
        sc = {Skill.BLOCKER:5, Skill.CLIMBER:10, Skill.FLOATER:10, Skill.BOMBER:6,
              Skill.BUILDER:15, Skill.BASHER:5, Skill.MINER:5, Skill.DIGGER:8}

    elif num == 15:
        total_count = 40; save_count = 25; release_rate = 20; time_limit = 600
        fill(0, 1050, W, H); fill(0, 1048, W, 1054); fill_steel(0, 1045, W, 1048)
        fill(50, 900, 250, 908); fill(350, 880, 550, 888)
        add_water(0, 960, 600, H)
        add_oneway(100, 895, 240, 900, ONEWAY_R)
        fill(600, 860, 1000, 868)
        add_fire(650, 850, 700, 860); add_fire(750, 850, 800, 860)
        add_fire(850, 850, 900, 860); add_fire(950, 850, 980, 860)
        fill_steel(600, 858, 1000, 860)
        fill(1100, 200, 1200, 1050)
        fill_steel(1100, 200, 1120, 1050); fill_steel(1180, 200, 1200, 1050)
        fill(1120, 900, 1180, 908); fill(1120, 750, 1180, 758)
        fill(1120, 600, 1180, 608); fill(1120, 450, 1180, 458); fill(1120, 300, 1180, 308)
        add_fire(1140, 740, 1160, 750); add_fire(1140, 590, 1160, 600)
        fill(1200, 200, 1500, 208); fill_steel(1200, 198, 1500, 200)
        add_trampoline(1150, 295, 1180, 300)
        fill(400, 350, 600, 358); fill(700, 300, 900, 308); fill(1000, 350, 1200, 358)
        add_water(200, 400, 400, 500); add_water(600, 400, 700, 500); add_water(900, 400, 1000, 500)
        add_spikes(250, 360, 380, 370)
        fill_steel(100, 200, 350, 220); fill_steel(100, 200, 120, 350)
        fill(100, 300, 300, 308); fill_steel(200, 250, 220, 300)
        add_water(130, 310, 190, 350)
        fill(50, 200, 100, 220)
        add_spikes(1120, 1000, 1180, 1050)
        add_pickup(450, 850, "floater"); add_pickup(800, 830, "climber")
        add_pickup(1150, 870, "builder"); add_pickup(1150, 720, "bomber")
        add_pickup(1150, 570, "digger"); add_pickup(1300, 270, "builder")
        add_pickup(500, 320, "basher"); add_pickup(150, 270, "miner")
        entrance = (120, 870); exit_pos = (70, 170)
        sc = {Skill.BLOCKER:6, Skill.CLIMBER:12, Skill.FLOATER:10, Skill.BOMBER:10,
              Skill.BUILDER:18, Skill.BASHER:12, Skill.MINER:10, Skill.DIGGER:10}

    else:
        total_count = 20; save_count = 12; release_rate = 35; time_limit = 300
        for x in range(W):
            h = int(800 + 80*math.sin(x*0.008) + 50*math.sin(x*0.02) + 30*math.sin(x*0.04))
            for y in range(h, H): set_t(x, y)
            set_t(x, h); set_t(x, h - 1)
        entrance = (150, 780); exit_pos = (W-200, 780)

    return {
        "terrain": terrain, "world_w": W, "world_h": H,
        "entrance": entrance, "exit_pos": exit_pos,
        "save_count": save_count, "total_count": total_count,
        "release_rate": release_rate, "skill_counts": sc,
        "pickups": pickups, "time_limit": time_limit,
    }

class Terrain:
    def __init__(self, data, world_w, world_h):
        self.data = bytearray(data)
        self.W = world_w; self.H = world_h
        self.surface = None; self._sky_surface = None; self._dirty = True
        self._sky_surface = pygame.Surface((world_w, world_h))
        for y in range(world_h):
            t = y / world_h
            r = int(COL_SKY_TOP[0] + (COL_SKY_BOT[0] - COL_SKY_TOP[0]) * t)
            g = int(COL_SKY_TOP[1] + (COL_SKY_BOT[1] - COL_SKY_TOP[1]) * t)
            b = int(COL_SKY_TOP[2] + (COL_SKY_BOT[2] - COL_SKY_TOP[2]) * t)
            pygame.draw.line(self._sky_surface, (r, g, b), (0, y), (world_w - 1, y))
        self._color_lut = []; self._deco_lut = []
        self._build_luts()

    def _build_luts(self):
        self._color_lut = []; self._deco_lut = []
        for i in range(self.W * self.H):
            x = i % self.W; y = i // self.W
            h = (x * 7 + y * 13) % 16
            above = True
            if y > 0:
                idx = (y - 1) * self.W + x
                v = self.data[idx] if idx < len(self.data) else SOLID
                above = v not in (SOLID, STEEL, TRAMPOLINE, ONEWAY_L, ONEWAY_R)
            if above: self._color_lut.append(COL_GRASS[h % 2])
            else: self._color_lut.append(COL_DIRT[h % len(COL_DIRT)])
            deco = 0
            if self.data[i] == SOLID and above:
                dh = (x * 31 + y * 17) % 200
                if dh < 3: deco = 1
                elif dh < 5: deco = 2
                elif dh < 7: deco = 3
            self._deco_lut.append(deco)

    def rebuild_lut(self):
        self._build_luts(); self._dirty = True

    def get(self, x, y):
        if 0 <= x < self.W and 0 <= y < self.H: return self.data[y * self.W + x]
        return SOLID

    def is_solid(self, x, y):
        v = self.get(x, y); return v in (SOLID, STEEL, TRAMPOLINE, ONEWAY_L, ONEWAY_R)

    def is_oneway(self, x, y):
        v = self.get(x, y); return v in (ONEWAY_L, ONEWAY_R)

    def oneway_dir(self, x, y):
        v = self.get(x, y)
        if v == ONEWAY_L: return -1
        if v == ONEWAY_R: return 1
        return 0

    def is_hazard(self, x, y):
        v = self.get(x, y); return v in (WATER, FIRE, SPIKE)

    def hazard_type(self, x, y):
        v = self.get(x, y)
        if v == WATER: return WATER
        if v == FIRE: return FIRE
        if v == SPIKE: return SPIKE
        return 0

    def set_solid(self, x, y, solid=True):
        if 0 <= x < self.W and 0 <= y < self.H:
            v = self.data[y * self.W + x]
            if v == STEEL or v == TRAMPOLINE: return
            self.data[y * self.W + x] = SOLID if solid else AIR
            self._dirty = True

    def remove_circle(self, cx, cy, radius):
        r2 = radius * radius
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= r2:
                    px, py = cx + dx, cy + dy
                    if 0 <= px < self.W and 0 <= py < self.H:
                        if self.data[py * self.W + px] not in (STEEL, TRAMPOLINE):
                            self.data[py * self.W + px] = AIR
        self._dirty = True

    def get_color(self, x, y, ticks=0):
        v = self.data[y * self.W + x]
        if v == STEEL:
            h = (x * 3 + y * 7) % 4; base = COL_STEEL
            return (base[0] - h * 3, base[1] - h * 3, base[2] - h * 2)
        if v == TRAMPOLINE:
            h = (x * 5 + y * 3) % 3
            return (max(0, COL_TRAMPOLINE[0] - h * 15), max(0, COL_TRAMPOLINE[1] - h * 20), COL_TRAMPOLINE[2])
        if v == ONEWAY_L or v == ONEWAY_R:
            h = (x * 3 + y * 5) % 3
            return (COL_ONEWAY[0] - h * 20, COL_ONEWAY[1] - h * 20, COL_ONEWAY[2])
        if v == WATER:
            wo = (x + ticks // 100) % 20; t = wo / 20.0
            return (int(COL_WATER_TOP[0]*(1-t)+COL_WATER_DEEP[0]*t),
                    int(COL_WATER_TOP[1]*(1-t)+COL_WATER_DEEP[1]*t),
                    int(COL_WATER_TOP[2]*(1-t)+COL_WATER_DEEP[2]*t))
        if v == FIRE:
            return COL_FIRE[(x + y + ticks // 80) % 3]
        if v == SPIKE:
            h = (x * 7 + y * 3) % 3; base = COL_SPIKE
            return (base[0] - h * 10, base[1] - h * 10, base[2] - h * 5)
        if v == SOLID: return self._color_lut[y * self.W + x]
        return None

    def render(self, screen, cam_x, cam_y, zoom=1.0):
        if self._dirty or self.surface is None:
            self.surface = pygame.Surface((self.W, self.H))
            self.surface.blit(self._sky_surface, (0, 0))
            pxarr = pygame.PixelArray(self.surface)
            ticks = pygame.time.get_ticks()
            for y in range(self.H):
                for x in range(self.W):
                    c = self.get_color(x, y, ticks)
                    if c: pxarr[x, y] = self.surface.map_rgb(c)
            del pxarr
            for i in range(self.W * self.H):
                if self._deco_lut[i] == 0: continue
                x = i % self.W; y = i // self.W
                if self.data[i] != SOLID: continue
                above = True
                if y > 0 and i >= self.W:
                    above = self.data[i - self.W] not in (SOLID, STEEL, TRAMPOLINE, ONEWAY_L, ONEWAY_R)
                if not above: continue
                if self._deco_lut[i] == 1:
                    pygame.draw.line(self.surface, COL_TREE_TRUNK, (x, y), (x, y - 6), 2)
                    lc = COL_TREE_LEAF[(x + y) % 3]
                    pygame.draw.circle(self.surface, lc, (x, y - 8), 4)
                elif self._deco_lut[i] == 2:
                    rc = COL_ROCK[(x + y) % 3]
                    pygame.draw.polygon(self.surface, rc, [(x-3, y), (x, y-4), (x+3, y)])
                elif self._deco_lut[i] == 3:
                    fc = COL_FLOWER[(x * 3 + y) % 4]
                    pygame.draw.line(self.surface, (0, 130, 0), (x, y), (x, y - 4), 1)
                    pygame.draw.circle(self.surface, fc, (x, y - 5), 2)
            self._dirty = False
        vw = int(GAME_W / zoom); vh = int(GAME_H / zoom)
        icx, icy = int(cam_x), int(cam_y)
        src = pygame.Rect(icx, icy, min(vw, self.W - icx), min(vh, self.H - icy))
        if src.width > 0 and src.height > 0:
            scaled = pygame.transform.scale(self.surface.subsurface(src), (GAME_W, GAME_H))
            screen.blit(scaled, (0, 0))
        else:
            screen.fill(COL_SKY_TOP, (0, 0, GAME_W, GAME_H))

    def render_minimap(self, size):
        scale = min(size / self.W, size / self.H)
        mw = int(self.W * scale); mh = int(self.H * scale)
        mm = pygame.Surface((mw, mh))
        for my in range(mh):
            for mx in range(mw):
                sx = int(mx / scale); sy = int(my / scale)
                v = self.data[sy * self.W + sx]
                if v == AIR: c = COL_SKY_BOT
                elif v == SOLID: c = COL_DIRT[0]
                elif v == STEEL: c = COL_STEEL
                elif v == WATER: c = COL_WATER_TOP
                elif v == FIRE: c = (200, 60, 0)
                elif v == SPIKE: c = (150, 150, 150)
                elif v == TRAMPOLINE: c = COL_TRAMPOLINE
                elif v in (ONEWAY_L, ONEWAY_R): c = COL_ONEWAY
                else: c = COL_DIRT[0]
                mm.set_at((mx, my), c)
        return mm

class Particle:
    def __init__(self, x, y, vx, vy, color, life, size=2):
        self.x = x; self.y = y; self.vx = vx; self.vy = vy
        self.color = color; self.life = self.max_life = life; self.size = size

    def update(self):
        self.x += self.vx; self.y += self.vy; self.vy += 0.15; self.life -= 1
        return self.life > 0

    def draw(self, screen, cx, cy, zoom):
        sx = int((self.x - cx) * zoom); sy = int((self.y - cy) * zoom)
        if 0 <= sx < GAME_W and 0 <= sy < GAME_H:
            s = max(1, int(self.size * zoom * (self.life / self.max_life)))
            pygame.draw.circle(screen, self.color, (sx, sy), s)

class Firework:
    def __init__(self, x, y):
        self.particles = []
        c1 = random.choice([(255,50,50),(50,255,50),(50,100,255),(255,255,50),(255,50,255),(50,255,255)])
        c2 = random.choice([(255,150,50),(150,255,50),(50,150,255),(255,255,150)])
        for _ in range(30):
            a = random.uniform(0, 2*math.pi); s = random.uniform(1, 4)
            self.particles.append(Particle(x, y, math.cos(a)*s, math.sin(a)*s,
                                           random.choice([c1, c2]), random.randint(30, 60), 2))
        self.alive = True

    def update(self):
        self.particles = [p for p in self.particles if p.update()]
        self.alive = len(self.particles) > 0; return self.alive

    def draw(self, screen, cx, cy, zoom):
        for p in self.particles: p.draw(screen, cx, cy, zoom)

class Pickup:
    def __init__(self, x, y, ptype):
        self.x = x; self.y = y; self.type = ptype
        self.collected = False; self.bob_offset = random.uniform(0, math.pi * 2)

    def draw(self, screen, cx, cy, zoom, ticks):
        if self.collected: return
        sx = int((self.x - cx) * zoom)
        sy = int((self.y - cy) * zoom) + int(3 * math.sin(ticks * 0.05 + self.bob_offset))
        if -10 < sx < GAME_W + 10 and -10 < sy < GAME_H + 10:
            glow = int(15 * abs(math.sin(ticks * 0.08 + self.bob_offset)))
            pygame.draw.circle(screen, (COL_PICKUP[0], COL_PICKUP[1], min(255, COL_PICKUP[2] + glow)),
                             (sx, sy), max(2, int(5 * zoom)))
            pygame.draw.circle(screen, WHITE, (sx, sy), max(1, int(3 * zoom)))

class Lemming:
    def __init__(self, x, y, direction=1):
        self.x = float(x); self.y = float(y); self.direction = direction
        self.state = LState.WALKING; self.alive = True; self.exited = False
        self.fall_dist = 0; self.bomb_timer = -1; self.build_count = 0
        self.bash_frames = 0; self.mine_frames = 0; self.exit_timer = 0
        self.dig_frames = 0; self.pickup_timer = 0
        self.is_climber = False; self.is_floater = False; self.floater_open = False
        self.anim_frame = 0; self.anim_timer = 0; self.step_cd = 0

    def assign_skill(self, skill, sounds=None):
        if not self.alive or self.exited: return False
        if self.state in (LState.EXPLODING, LState.EXITING, LState.SPLATTING,
                          LState.DROWNING, LState.BURNING, LState.DEAD, LState.PICKING_UP): return False
        if skill == Skill.BLOCKER:
            if self.state == LState.WALKING:
                self.state = LState.BLOCKING
                if sounds: sounds["click"].play(); return True
        elif skill == Skill.CLIMBER:
            self.is_climber = True
            if sounds: sounds["click"].play(); return True
        elif skill == Skill.FLOATER:
            self.is_floater = True
            if sounds: sounds["click"].play(); return True
        elif skill == Skill.BOMBER:
            if self.state != LState.BLOCKING:
                self.state = LState.EXPLODING; self.bomb_timer = 60
                if sounds: sounds["click"].play(); return True
        elif skill == Skill.BUILDER:
            if self.state == LState.WALKING:
                self.state = LState.BUILDING; self.build_count = 0
                if sounds: sounds["click"].play(); return True
        elif skill == Skill.BASHER:
            if self.state == LState.WALKING:
                self.state = LState.BASHING; self.bash_frames = 0
                if sounds: sounds["click"].play(); return True
        elif skill == Skill.MINER:
            if self.state == LState.WALKING:
                self.state = LState.MINING; self.mine_frames = 0
                if sounds: sounds["click"].play(); return True
        elif skill == Skill.DIGGER:
            if self.state == LState.WALKING:
                self.state = LState.DIGGING; self.dig_frames = 0
                if sounds: sounds["click"].play(); return True
        return False

    def update(self, terrain, sounds=None, pickups=None):
        if not self.alive or self.exited: return None
        self.anim_timer += 1
        if self.anim_timer >= 8: self.anim_timer = 0; self.anim_frame = (self.anim_frame + 1) % 4
        if self.step_cd > 0: self.step_cd -= 1

        if self.state in (LState.WALKING, LState.FALLING) and pickups:
            for p in pickups:
                if not p.collected and abs(self.x - p.x) < 8 and abs(self.y - p.y) < 8:
                    p.collected = True; self.state = LState.PICKING_UP; self.pickup_timer = 20
                    if sounds: sounds["pickup"].play()
                    return p

        if self.state == LState.PICKING_UP:
            self.pickup_timer -= 1
            if self.pickup_timer <= 0: self.state = LState.WALKING
            return None

        if self.state == LState.WALKING:
            nx = self.x + self.direction * WALK_SPEED
            if terrain.is_oneway(int(nx), int(self.y)):
                od = terrain.oneway_dir(int(nx), int(self.y))
                if od != 0 and od != self.direction: self.direction *= -1; return None
            if terrain.is_solid(int(nx), int(self.y)):
                can_climb = False
                if self.is_climber:
                    if not terrain.is_solid(int(nx), int(self.y) - 1) and terrain.is_solid(int(nx), int(self.y) - 2):
                        can_climb = True
                if can_climb: self.state = LState.CLIMBING
                else: self.direction *= -1
                return None
            self.x = nx
            if not terrain.is_solid(int(self.x), int(self.y) + 1):
                self.state = LState.FALLING; self.fall_dist = 0
            if self.step_cd <= 0 and terrain.is_solid(int(self.x), int(self.y) + 1) and sounds:
                sounds["step"].play(); self.step_cd = 12
            return None

        elif self.state == LState.FALLING:
            self.fall_dist += 1
            if self.is_floater and self.fall_dist > 8 and not self.floater_open: self.floater_open = True
            if self.is_floater and self.floater_open: self.y += 0.5
            else: self.y += GRAVITY * 2
            if terrain.is_solid(int(self.x), int(self.y) + 1):
                if self.fall_dist > 60 and not (self.is_floater and self.floater_open):
                    self.state = LState.SPLATTING; self.alive = False
                    if sounds: sounds["splat"].play(); return None
                self.y = int(self.y); self.state = LState.WALKING
                self.fall_dist = 0; self.floater_open = False; return None
            ht = terrain.hazard_type(int(self.x), int(self.y))
            if ht == WATER:
                self.state = LState.DROWNING; self.alive = False
                if sounds: sounds["splash"].play()
            elif ht == FIRE:
                self.state = LState.BURNING; self.alive = False
                if sounds: sounds["burn"].play()
            elif ht == SPIKE:
                self.state = LState.DEAD; self.alive = False
                if sounds: sounds["splat"].play()
            tv = terrain.get(int(self.x), int(self.y) + 1)
            if tv == TRAMPOLINE:
                self.y -= 80; self.fall_dist = 0; self.floater_open = False
                if sounds: sounds["bounce"].play()
            return None

        elif self.state == LState.CLIMBING:
            self.y -= CLIMB_SPEED
            if not terrain.is_solid(int(self.x), int(self.y) - 1):
                self.y -= 1; self.state = LState.WALKING; self.fall_dist = 0
            return None

        elif self.state == LState.BLOCKING:
            if not terrain.is_solid(int(self.x), int(self.y) + 1):
                self.state = LState.FALLING; self.fall_dist = 0
            return None

        elif self.state == LState.BUILDING:
            self.build_count += 1
            bx = self.x + self.direction * 2; by = self.y - 1
            terrain.set_solid(int(bx), int(by), True)
            terrain.set_solid(int(bx + self.direction), int(by), True)
            if self.build_count > 0 and self.build_count % 3 == 0:
                self.x += self.direction * 2; self.y -= 1
                if sounds and self.build_count % 6 == 0: sounds["build_place"].play()
            if self.build_count >= 12: self.state = LState.WALKING; self.build_count = 0
            if terrain.is_solid(int(self.x + self.direction * 2), int(self.y - 2)):
                self.state = LState.WALKING; self.build_count = 0
            return None

        elif self.state == LState.BASHING:
            self.bash_frames += 1
            if self.bash_frames % 3 == 0:
                cx = self.x + self.direction * 5
                terrain.remove_circle(int(cx), int(self.y), 3)
                if sounds and self.bash_frames % 9 == 0: sounds["dig"].play()
            self.x += self.direction * WALK_SPEED
            if not terrain.is_solid(int(self.x + self.direction * 3), int(self.y)):
                self.state = LState.WALKING
            if not terrain.is_solid(int(self.x), int(self.y) + 1):
                self.state = LState.FALLING; self.fall_dist = 0
            return None

        elif self.state == LState.MINING:
            self.mine_frames += 1
            if self.mine_frames % 3 == 0:
                for oy in range(3):
                    for ox in range(3):
                        terrain.set_solid(int(self.x) + self.direction * 2 + ox, int(self.y) + oy, False)
                if sounds and self.mine_frames % 9 == 0: sounds["dig"].play()
            self.x += self.direction * WALK_SPEED * 0.5; self.y += 0.5
            if self.mine_frames > 150: self.state = LState.WALKING
            return None

        elif self.state == LState.DIGGING:
            self.dig_frames += 1
            if self.dig_frames % 3 == 0:
                for dx in range(-3, 4):
                    terrain.set_solid(int(self.x) + dx, int(self.y) + 2, False)
                if sounds and self.dig_frames % 9 == 0: sounds["dig"].play()
            self.y += 0.5
            if not terrain.is_solid(int(self.x), int(self.y) + 3):
                self.state = LState.FALLING; self.fall_dist = 0
            if self.dig_frames > 200: self.state = LState.WALKING
            return None

        elif self.state == LState.EXPLODING:
            self.bomb_timer -= 1
            if self.bomb_timer == 20 and sounds: sounds["warning"].play()
            if self.bomb_timer <= 0:
                if sounds: sounds["boom"].play()
                terrain.remove_circle(int(self.x), int(self.y), 12)
                self.alive = False; self.state = LState.DEAD
            return None
        return None

    def draw(self, screen, cx, cy, zoom):
        if not self.alive: return
        x = int((self.x - cx) * zoom); y = int((self.y - cy) * zoom)
        if x < -20 or x > GAME_W + 20 or y < -20 or y > GAME_H + 20: return
        d = self.direction; af = self.anim_frame

        if self.state == LState.DROWNING:
            for i in range(3):
                dy = -5 + i * 4; dx = int(3 * math.sin(self.anim_timer * 0.3 + i))
                pygame.draw.circle(screen, (100, 150, 255), (x + dx, y + dy), max(1, int(2 * zoom)))
            return
        if self.state == LState.BURNING:
            c = COL_FIRE[self.anim_frame % 3]
            pygame.draw.circle(screen, c, (x, y - 4), max(2, int(4 * zoom)))
            pygame.draw.circle(screen, (255, 255, 100), (x, y - 7), max(1, int(2 * zoom)))
            return
        if self.state == LState.SPLATTING:
            pygame.draw.ellipse(screen, COL_LR, (x - 5, y - 1, 10, 3))
            return

        lo = int(2 * math.sin(af * math.pi / 2)) if self.state == LState.WALKING else 0
        bc = COL_LB
        pygame.draw.line(screen, bc, (x - 1, y + 1), (x - 1 - lo, y + 5), max(1, int(2 * zoom)))
        pygame.draw.line(screen, bc, (x + 1, y + 1), (x + 1 + lo, y + 5), max(1, int(2 * zoom)))
        pygame.draw.rect(screen, COL_LB, (x - 3, y - 6, 6, 7))
        pygame.draw.circle(screen, COL_LR, (x, y - 9), max(2, int(4 * zoom)))
        pygame.draw.line(screen, COL_LH, (x - 3, y - 12), (x + 3, y - 12), max(1, int(2 * zoom)))
        pygame.draw.line(screen, COL_LH, (x - 2, y - 13), (x + 2, y - 13), max(1, int(1 * zoom)))
        ex = x + d * 2
        pygame.draw.circle(screen, BLACK, (ex, y - 10), max(1, int(1 * zoom)))
        pygame.draw.line(screen, bc, (x + 1, y - 5), (x + 1 + lo, y + 1), 2)
        pygame.draw.line(screen, bc, (x - 1, y - 5), (x - 1 - lo, y + 1), 2)

        if self.is_climber and self.state in (LState.WALKING, LState.CLIMBING, LState.FALLING):
            pygame.draw.line(screen, WHITE, (x, y - 13), (x, y - 17), 1)
            pygame.draw.line(screen, WHITE, (x, y - 17), (x + 3, y - 15), 1)
            pygame.draw.line(screen, WHITE, (x, y - 17), (x - 3, y - 15), 1)
        if self.is_floater and self.state == LState.FALLING and self.floater_open:
            pygame.draw.line(screen, (255, 255, 100), (x, y - 13), (x, y - 25), 1)
            pygame.draw.arc(screen, (255, 255, 100), (x - 8, y - 32, 16, 12), 0, math.pi, 1)
        if self.state == LState.BLOCKING:
            pygame.draw.circle(screen, WHITE, (x, y - 9), 7, 1)
            pygame.draw.line(screen, WHITE, (x - 5, y - 9), (x + 5, y - 9), 1)
            pygame.draw.line(screen, WHITE, (x, y - 14), (x, y - 4), 1)
        if self.state == LState.BUILDING:
            pygame.draw.rect(screen, COL_DIRT[0], (x + d * 4 - 2, y - 2, 5, 3))
        if self.state == LState.EXPLODING and self.bomb_timer % 6 < 3:
            pygame.draw.circle(screen, (255, 255, 0), (x, y - 5), 8, 1)
        if self.state == LState.PICKING_UP:
            r = int(6 * (1 - self.pickup_timer / 20))
            pygame.draw.circle(screen, COL_PICKUP, (x, y - 12), r, 1)
        if self.state == LState.EXITING:
            s = max(0, self.exit_timer / 30)
            pygame.draw.circle(screen, COL_EXIT, (x, y - 5), max(1, int(5 * s)))

class LevelEditor:
    TOOL_SOLID = 0; TOOL_STEEL = 1; TOOL_WATER = 2; TOOL_FIRE = 3
    TOOL_SPIKE = 4; TOOL_ERASER = 5; TOOL_ENTRANCE = 6; TOOL_EXIT = 7
    TOOL_TRAMPOLINE = 8; TOOL_ONEWAY_L = 9; TOOL_ONEWAY_R = 10
    TOOL_FILL = 11; TOOL_LINE = 12
    TOOL_NAMES = {0:"Solid",1:"Steel",2:"Water",3:"Fire",4:"Spike",5:"Erase",
                  6:"Entr",7:"Exit",8:"Tramp",9:"<Way",10:">Way",11:"Fill",12:"Line"}
    TOOL_COLORS = {0:COL_DIRT[0],1:COL_STEEL,2:COL_WATER_TOP,3:COL_FIRE[0],4:COL_SPIKE,
                   5:(80,80,80),6:COL_ENTRANCE,7:COL_EXIT,8:COL_TRAMPOLINE,
                   9:COL_ONEWAY,10:COL_ONEWAY,11:(100,200,100),12:(200,200,100)}
    TOOL_TERRAIN = {0:SOLID,1:STEEL,2:WATER,3:FIRE,4:SPIKE,8:TRAMPOLINE,9:ONEWAY_L,10:ONEWAY_R}

    def __init__(self, game):
        self.game = game
        self.terrain = Terrain(bytearray(1600 * 1200), 1600, 1200)
        self.entrance = [200, 800]; self.exit_pos = [1400, 800]
        self.tool = self.TOOL_SOLID
        self.brush_sizes = [1, 3, 5, 10, 20]; self.brush_idx = 2
        self.show_grid = False; self.mirror_x = False; self.painting = False
        self.cam_x = 0.0; self.cam_y = 0.0; self.minimap_surf = None
        self.level_name = "My Level"; self.total_count = 20; self.save_count = 10
        self.release_rate = 35; self.time_limit = 300
        self.skill_counts = {s:5 for s in [Skill.BLOCKER,Skill.CLIMBER,Skill.FLOATER,Skill.BOMBER,
                                          Skill.BUILDER,Skill.BASHER,Skill.MINER,Skill.DIGGER]}
        self.undo_stack = []; self.redo_stack = []; self._unsaved = False
        self.params_open = False; self.param_cursor = 0
        self.show_file_dialog = None; self.file_list = []; self.file_name_input = ""
        self.file_scroll = 0; self.file_selected = -1
        self.custom_levels_dir = LEVELS_DIR; self.toolbar_h = 40
        self.toolbar_buttons = []; self._line_start = None
        self._build_toolbar()

    def _build_toolbar(self):
        self.toolbar_buttons = []; bx = 5
        for tid in [self.TOOL_SOLID,self.TOOL_STEEL,self.TOOL_WATER,self.TOOL_FIRE,
                     self.TOOL_SPIKE,self.TOOL_ERASER,self.TOOL_TRAMPOLINE,
                     self.TOOL_ONEWAY_L,self.TOOL_ONEWAY_R,self.TOOL_FILL,self.TOOL_LINE,
                     self.TOOL_ENTRANCE,self.TOOL_EXIT]:
            self.toolbar_buttons.append((pygame.Rect(bx,3,48,32), tid, self.TOOL_NAMES.get(tid,"?")))
            bx += 51
        bx += 5
        for i in range(len(self.brush_sizes)):
            self.toolbar_buttons.append((pygame.Rect(bx,3,30,32), 100+i, f"B{self.brush_sizes[i]}"))
            bx += 33
        bx += 5
        for aid, al in [(200,"Undo"),(201,"Redo"),(202,"Grid"),(203,"Param"),(204,"Floor"),
                        (205,"Hills"),(206,"Mirror"),(207,"Test"),(208,"Save"),(209,"Load"),
                        (210,"Clear"),(211,"Back")]:
            self.toolbar_buttons.append((pygame.Rect(bx,3,44,32), aid, al))
            bx += 47

    def push_undo(self):
        self.undo_stack.append(bytearray(self.terrain.data))
        if len(self.undo_stack) > 50: self.undo_stack.pop(0)
        self.redo_stack.clear(); self._unsaved = True

    def undo(self):
        if not self.undo_stack: return
        self.redo_stack.append(bytearray(self.terrain.data))
        self.terrain.data = self.undo_stack.pop()
        self.terrain._dirty = True; self.terrain.rebuild_lut()

    def redo(self):
        if not self.redo_stack: return
        self.undo_stack.append(bytearray(self.terrain.data))
        self.terrain.data = self.redo_stack.pop()
        self.terrain._dirty = True; self.terrain.rebuild_lut()

    def paint(self, wx, wy):
        bs = self.brush_sizes[self.brush_idx]
        if self.tool == self.TOOL_ENTRANCE: self.entrance = [wx, wy]; return
        if self.tool == self.TOOL_EXIT: self.exit_pos = [wx, wy]; return
        if self.tool == self.TOOL_FILL: self._flood_fill(int(wx), int(wy)); return
        tv = self.TOOL_TERRAIN.get(self.tool, AIR)
        is_eraser = (self.tool == self.TOOL_ERASER)
        r = bs // 2
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx*dx + dy*dy <= r*r:
                    px, py = wx + dx, wy + dy
                    if 0 <= px < self.terrain.W and 0 <= py < self.terrain.H:
                        if is_eraser:
                            if self.terrain.data[py * self.terrain.W + px] != STEEL:
                                self.terrain.data[py * self.terrain.W + px] = AIR
                        else:
                            self.terrain.data[py * self.terrain.W + px] = tv
        if self.mirror_x:
            mx = self.terrain.W - wx
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx*dx + dy*dy <= r*r:
                        px, py = mx + dx, wy + dy
                        if 0 <= px < self.terrain.W and 0 <= py < self.terrain.H:
                            if is_eraser:
                                if self.terrain.data[py * self.terrain.W + px] != STEEL:
                                    self.terrain.data[py * self.terrain.W + px] = AIR
                            else:
                                self.terrain.data[py * self.terrain.W + px] = tv
        self.terrain._dirty = True

    def _flood_fill(self, sx, sy):
        if not (0 <= sx < self.terrain.W and 0 <= sy < self.terrain.H): return
        target = self.terrain.data[sy * self.terrain.W + sx]
        fill_v = self.TOOL_TERRAIN.get(self.tool, SOLID)
        if target == fill_v or target == STEEL: return
        stack = [(sx, sy)]; visited = set(); limit = 200000
        while stack and limit > 0:
            x, y = stack.pop()
            if (x, y) in visited: continue
            if not (0 <= x < self.terrain.W and 0 <= y < self.terrain.H): continue
            if self.terrain.data[y * self.terrain.W + x] != target: continue
            visited.add((x, y)); self.terrain.data[y * self.terrain.W + x] = fill_v; limit -= 1
            stack.append((x+1,y)); stack.append((x-1,y))
            stack.append((x,y+1)); stack.append((x,y-1))
        self.terrain._dirty = True

    def paint_line(self, x1, y1, x2, y2):
        dx = abs(x2-x1); dy = abs(y2-y1); steps = max(dx, dy, 1)
        for i in range(steps + 1):
            t = i / steps
            self.paint(int(x1 + (x2-x1)*t), int(y1 + (y2-y1)*t))

    def do_floor(self):
        self.push_undo()
        for x in range(self.terrain.W):
            self.terrain.data[1000*self.terrain.W+x] = SOLID
            self.terrain.data[1001*self.terrain.W+x] = SOLID
        self.terrain._dirty = True; self.terrain.rebuild_lut()

    def do_hills(self):
        self.push_undo(); W, H = self.terrain.W, self.terrain.H
        for x in range(W):
            h = int(800 + 80*math.sin(x*0.008) + 50*math.sin(x*0.02) + 30*math.sin(x*0.04))
            for y in range(h, H): self.terrain.data[y*W+x] = SOLID
            self.terrain.data[h*W+x] = SOLID
            if h > 0: self.terrain.data[(h-1)*W+x] = SOLID
        self.terrain._dirty = True; self.terrain.rebuild_lut()

    def save_level(self, path):
        try: os.makedirs(os.path.dirname(path), exist_ok=True)
        except: pass
        data = {"name":self.level_name,"terrain_b64":base64.b64encode(bytes(self.terrain.data)).decode(),
                "world_w":self.terrain.W,"world_h":self.terrain.H,"entrance":self.entrance,
                "exit_pos":self.exit_pos,"total_count":self.total_count,"save_count":self.save_count,
                "release_rate":self.release_rate,"time_limit":self.time_limit,
                "skill_counts":{str(k):v for k,v in self.skill_counts.items()}}
        with open(path,'w') as f: json.dump(data, f)
        self._unsaved = False

    def load_level(self, path):
        with open(path,'r') as f: data = json.load(f)
        tb = bytearray(base64.b64decode(data["terrain_b64"]))
        self.terrain = Terrain(tb, data["world_w"], data["world_h"])
        self.entrance = list(data["entrance"]); self.exit_pos = list(data["exit_pos"])
        self.level_name = data.get("name","Custom")
        self.total_count = data.get("total_count",20); self.save_count = data.get("save_count",10)
        self.release_rate = data.get("release_rate",35); self.time_limit = data.get("time_limit",300)
        sc = {int(k):v for k,v in data.get("skill_counts",{}).items()}
        for s in [Skill.BLOCKER,Skill.CLIMBER,Skill.FLOATER,Skill.BOMBER,
                  Skill.BUILDER,Skill.BASHER,Skill.MINER,Skill.DIGGER]:
            if s not in sc: sc[s] = 0
        self.skill_counts = sc; self.undo_stack.clear(); self.redo_stack.clear(); self._unsaved = False

    def test_play(self):
        return {"terrain":bytearray(self.terrain.data),"world_w":self.terrain.W,
                "world_h":self.terrain.H,"entrance":tuple(self.entrance),
                "exit_pos":tuple(self.exit_pos),"save_count":self.save_count,
                "total_count":self.total_count,"release_rate":self.release_rate,
                "time_limit":self.time_limit,"skill_counts":dict(self.skill_counts),"pickups":[]}

    def update(self): pass

    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: return False
            if self.params_open: self._handle_params_event(ev); continue
            if self.show_file_dialog: self._handle_file_dialog_event(ev); continue
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if self._unsaved: self.show_file_dialog = "unsaved"
                    else: self.game.state = "menu"
                    return True
                elif ev.key == pygame.K_g: self.show_grid = not self.show_grid
                elif ev.key == pygame.K_m: self.mirror_x = not self.mirror_x
                elif ev.key == pygame.K_t:
                    self.game.test_play_data = self.test_play()
                    self.game.test_play_name = self.level_name
                    self.game.testing_from_editor = True
                    self.game.init_level_from_data(self.game.test_play_data, self.game.test_play_name)
                    self.game.state = "playing"; return True
                elif ev.key == pygame.K_p: self.params_open = True; self.param_cursor = 0
                elif ev.key == pygame.K_z and (ev.mod & pygame.KMOD_CTRL):
                    if ev.mod & pygame.KMOD_SHIFT: self.redo()
                    else: self.undo()
                elif ev.key == pygame.K_s and (ev.mod & pygame.KMOD_CTRL): self._open_save_dialog()
                elif ev.key == pygame.K_l and (ev.mod & pygame.KMOD_CTRL): self._open_load_dialog()
                elif ev.key == pygame.K_LEFTBRACKET: self.brush_idx = max(0, self.brush_idx-1)
                elif ev.key == pygame.K_RIGHTBRACKET: self.brush_idx = min(len(self.brush_sizes)-1, self.brush_idx+1)
            if ev.type == pygame.MOUSEWHEEL:
                if ev.y > 0: self.brush_idx = min(len(self.brush_sizes)-1, self.brush_idx+1)
                elif ev.y < 0: self.brush_idx = max(0, self.brush_idx-1)
            if ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos; clicked = False
                for rect, tid, _ in self.toolbar_buttons:
                    if rect.collidepoint(mx, my):
                        clicked = True; self._handle_toolbar_click(tid); break
                if not clicked and mx < GAME_W and my > self.toolbar_h:
                    if ev.button == 1:
                        if self.tool == self.TOOL_LINE:
                            wx, wy = mx + self.cam_x, my + self.cam_y
                            if self._line_start is None: self._line_start = (wx, wy); self.push_undo()
                            else: self.paint_line(self._line_start[0], self._line_start[1], wx, wy); self._line_start = None; self.terrain.rebuild_lut()
                        else:
                            self.painting = True; self.push_undo()
                            self.paint(mx + self.cam_x, my + self.cam_y)
                    elif ev.button == 3:
                        self.painting = True; self.push_undo()
                        old = self.tool; self.tool = self.TOOL_ERASER
                        self.paint(mx + self.cam_x, my + self.cam_y); self.tool = old
            if ev.type == pygame.MOUSEBUTTONUP:
                self.painting = False
                if self.tool != self.TOOL_LINE: self.terrain.rebuild_lut()
            if ev.type == pygame.MOUSEMOTION and self.painting:
                mx, my = ev.pos
                if mx < GAME_W and my > self.toolbar_h:
                    self.paint(mx + self.cam_x, my + self.cam_y)
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mx, my = ev.pos
                mm_x, mm_y, mm_s = GAME_W-130, self.toolbar_h+5, 120
                if mm_x <= mx <= mm_x+mm_s and mm_y <= my <= my+mm_s:
                    self.cam_x = int((mx-mm_x)/mm_s*self.terrain.W) - GAME_W//2
                    self.cam_y = int((my-mm_y)/mm_s*self.terrain.H) - GAME_H//2
                    self._clamp_camera()
        return True

    def _handle_toolbar_click(self, tid):
        if tid <= self.TOOL_LINE: self.tool = tid; self._line_start = None
        elif 100 <= tid < 200: self.brush_idx = tid - 100
        elif tid == 200: self.undo()
        elif tid == 201: self.redo()
        elif tid == 202: self.show_grid = not self.show_grid
        elif tid == 203: self.params_open = True; self.param_cursor = 0
        elif tid == 204: self.do_floor()
        elif tid == 205: self.do_hills()
        elif tid == 206: self.mirror_x = not self.mirror_x
        elif tid == 207:
            self.game.test_play_data = self.test_play()
            self.game.test_play_name = self.level_name
            self.game.testing_from_editor = True
            self.game.init_level_from_data(self.game.test_play_data, self.game.test_play_name)
            self.game.state = "playing"
        elif tid == 208: self._open_save_dialog()
        elif tid == 209: self._open_load_dialog()
        elif tid == 210:
            self.push_undo(); self.terrain.data = bytearray(1600*1200); self.terrain._dirty = True
            self.entrance = [200,800]; self.exit_pos = [1400,800]
        elif tid == 211:
            if self._unsaved: self.show_file_dialog = "unsaved"
            else: self.game.state = "menu"

    def _open_save_dialog(self):
        self.file_name_input = self.level_name.replace(" ","_").lower()
        self.show_file_dialog = "save"; self.file_scroll = 0; self.file_selected = -1

    def _open_load_dialog(self):
        self._refresh_file_list()
        self.show_file_dialog = "load"; self.file_scroll = 0; self.file_selected = -1

    def _refresh_file_list(self):
        self.file_list = []
        if os.path.isdir(self.custom_levels_dir):
            for f in sorted(os.listdir(self.custom_levels_dir)):
                if f.endswith('.json'): self.file_list.append(f)

    def _handle_params_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_RETURN): self.params_open = False
            elif ev.key == pygame.K_UP: self.param_cursor = max(0, self.param_cursor-1)
            elif ev.key == pygame.K_DOWN: self.param_cursor = min(13, self.param_cursor+1)
            elif ev.key == pygame.K_LEFT: self._adjust_param(-1)
            elif ev.key == pygame.K_RIGHT: self._adjust_param(1)
            elif ev.key == pygame.K_BACKSPACE and self.param_cursor == 0 and len(self.level_name) > 0:
                self.level_name = self.level_name[:-1]
            elif ev.unicode and ev.unicode.isprintable() and self.param_cursor == 0 and len(self.level_name) < 30:
                self.level_name += ev.unicode
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mx, my = ev.pos; ox, oy = SCREEN_W//2-180, SCREEN_H//2-220
            for i in range(14):
                ry = oy + 60 + i*30
                if ox <= mx <= ox+360 and ry <= my <= ry+28: self.param_cursor = i; break

    def _adjust_param(self, d):
        if self.param_cursor == 1: self.total_count = max(5,min(100,self.total_count+d))
        elif self.param_cursor == 2: self.save_count = max(1,min(self.total_count,self.save_count+d))
        elif self.param_cursor == 3: self.release_rate = max(5,min(120,self.release_rate+d*5))
        elif self.param_cursor == 4: self.time_limit = max(60,min(999,self.time_limit+d*30))
        else:
            skills = [Skill.BLOCKER,Skill.CLIMBER,Skill.FLOATER,Skill.BOMBER,
                      Skill.BUILDER,Skill.BASHER,Skill.MINER,Skill.DIGGER]
            idx = self.param_cursor - 5
            if 0 <= idx < len(skills):
                s = skills[idx]; self.skill_counts[s] = max(0,min(99,self.skill_counts.get(s,0)+d))

    def _handle_file_dialog_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE: self.show_file_dialog = None; return
            if self.show_file_dialog == "save":
                if ev.key == pygame.K_RETURN and self.file_name_input:
                    fn = self.file_name_input
                    if not fn.endswith('.json'): fn += '.json'
                    self.save_level(os.path.join(self.custom_levels_dir, fn))
                    self.show_file_dialog = None
                elif ev.key == pygame.K_BACKSPACE: self.file_name_input = self.file_name_input[:-1]
                elif ev.unicode and ev.unicode.isprintable() and len(self.file_name_input) < 50:
                    self.file_name_input += ev.unicode
            elif self.show_file_dialog == "load":
                if ev.key == pygame.K_RETURN and 0 <= self.file_selected < len(self.file_list):
                    self.load_level(os.path.join(self.custom_levels_dir, self.file_list[self.file_selected]))
                    self.show_file_dialog = None
                elif ev.key == pygame.K_UP: self.file_selected = max(0, self.file_selected-1)
                elif ev.key == pygame.K_DOWN: self.file_selected = min(len(self.file_list)-1, self.file_selected+1)
            elif self.show_file_dialog == "unsaved":
                if ev.key == pygame.K_y: self.game.state = "menu"; self.show_file_dialog = None
                elif ev.key in (pygame.K_n, pygame.K_ESCAPE): self.show_file_dialog = None
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mx, my = ev.pos
            if self.show_file_dialog == "load":
                ox, oy = SCREEN_W//2-180, SCREEN_H//2-120
                for i, fn in enumerate(self.file_list):
                    fy = oy + 60 + i*28 - self.file_scroll
                    if ox <= mx <= ox+360 and fy <= my <= fy+26:
                        self.file_selected = i
                        if pygame.time.get_ticks()-getattr(self,'_lfc',0) < 400 and self.file_selected == getattr(self,'_lfi',-1):
                            self.load_level(os.path.join(self.custom_levels_dir, fn))
                            self.show_file_dialog = None
                        self._lfc = pygame.time.get_ticks(); self._lfi = i; break
            elif self.show_file_dialog == "unsaved":
                cx = SCREEN_W // 2
                if cx-100<=mx<=cx-10 and SCREEN_H//2+30<=my<=SCREEN_H//2+60:
                    self.game.state = "menu"; self.show_file_dialog = None
                elif cx+10<=mx<=cx+100 and SCREEN_H//2+30<=my<=SCREEN_H//2+60:
                    self.show_file_dialog = None

    def _clamp_camera(self):
        self.cam_x = max(0, min(int(self.cam_x), self.terrain.W - GAME_W))
        self.cam_y = max(0, min(int(self.cam_y), self.terrain.H - GAME_H))

    def _update_camera(self):
        keys = pygame.key.get_pressed(); spd = 8
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.cam_x -= spd
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.cam_x += spd
        if keys[pygame.K_UP] or keys[pygame.K_w]: self.cam_y -= spd
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: self.cam_y += spd
        mx, my = pygame.mouse.get_pos()
        if my > self.toolbar_h:
            if mx < 20: self.cam_x -= spd
            elif mx > GAME_W-20 and mx < GAME_W: self.cam_x += spd
            if my < 20+self.toolbar_h: self.cam_y -= spd
            elif my > GAME_H-20: self.cam_y += spd
        self._clamp_camera()

    def draw(self):
        self._update_camera()
        screen = self.game.screen; cx, cy = self.cam_x, self.cam_y
        self.terrain.render(screen, cx, cy, zoom=1.0)
        if self.show_grid:
            gs = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
            sx = -(int(cx)%20); sy = -(int(cy)%20)
            for gx in range(sx, GAME_W, 20): pygame.draw.line(gs, (255,255,255,30), (gx,0), (gx,GAME_H))
            for gy in range(sy, GAME_H, 20): pygame.draw.line(gs, (255,255,255,30), (0,gy), (GAME_W,gy))
            screen.blit(gs, (0,0))
        if self.tool == self.TOOL_LINE and self._line_start:
            mx, my = pygame.mouse.get_pos()
            pygame.draw.line(screen, (255,255,0), (int(self._line_start[0]-cx), int(self._line_start[1]-cy)), (mx,my), 1)
        # Entrance/Exit markers
        ex, ey = int(self.entrance[0]-cx), int(self.entrance[1]-cy)
        pygame.draw.rect(screen, COL_ENTRANCE, (ex-12, ey-15, 24, 18))
        t = self.game.font_sm.render("IN", True, WHITE); screen.blit(t, (ex-7, ey-13))
        ex2, ey2 = int(self.exit_pos[0]-cx), int(self.exit_pos[1]-cy)
        pygame.draw.rect(screen, COL_EXIT, (ex2-12, ey2-15, 24, 18))
        t = self.game.font_sm.render("OUT", True, WHITE); screen.blit(t, (ex2-10, ey2-13))
        if self.mirror_x:
            mx_line = int(self.terrain.W//2 - cx)
            pygame.draw.line(screen, (255,100,100), (mx_line,0), (mx_line,GAME_H), 1)
        # Minimap
        if self.minimap_surf is None: self.minimap_surf = self.terrain.render_minimap(120)
        mm = self.minimap_surf; mmx, mmy = GAME_W-130, self.toolbar_h+5
        pygame.draw.rect(screen, BLACK, (mmx-2,mmy-2,124,124))
        screen.blit(mm, (mmx, mmy))
        sr = pygame.Rect(int(cx/self.terrain.W*120), int(cy/self.terrain.H*120),
                        int(GAME_W/self.terrain.W*120), int(GAME_H/self.terrain.H*120))
        pygame.draw.rect(screen, WHITE, (mmx+sr.x, mmy+sr.y, sr.w, sr.h), 1)
        # Brush cursor
        mx, my = pygame.mouse.get_pos()
        if mx < GAME_W and my > self.toolbar_h:
            bs = self.brush_sizes[self.brush_idx]
            tc = self.TOOL_COLORS.get(self.tool, WHITE)
            pygame.draw.circle(screen, tc, (mx, my), bs//2, 1)
        # Toolbar
        pygame.draw.rect(screen, COL_UI_BG, (0,0,GAME_W,self.toolbar_h))
        pygame.draw.line(screen, COL_UI_BORDER, (0,self.toolbar_h), (GAME_W,self.toolbar_h), 2)
        for rect, tid, label in self.toolbar_buttons:
            sel = (tid == self.tool) if tid <= self.TOOL_LINE else False
            bg = COL_UI_SK_SEL if sel else COL_UI_SK
            pygame.draw.rect(screen, bg, rect, border_radius=3)
            if sel: pygame.draw.rect(screen, COL_UI_HL, rect, 2, border_radius=3)
            t = self.game.font_sm.render(label, True, WHITE if sel else COL_UI_TEXT)
            screen.blit(t, (rect.x+(rect.w-t.get_width())//2, rect.y+(rect.h-t.get_height())//2))
        # Info
        info = f"Tool: {self.TOOL_NAMES.get(self.tool,'?')}  Brush: {self.brush_sizes[self.brush_idx]}  Mirror: {'ON' if self.mirror_x else 'OFF'}"
        if self._unsaved: info += "  [UNSAVED]"
        t = self.game.font_sm.render(info, True, COL_UI_HL)
        bg = pygame.Surface((t.get_width()+10, t.get_height()+4), pygame.SRCALPHA); bg.fill((0,0,0,140))
        screen.blit(bg, (4, self.toolbar_h+2)); screen.blit(t, (9, self.toolbar_h+4))
        if self.params_open: self._draw_params()
        if self.show_file_dialog: self._draw_file_dialog()

    def _draw_params(self):
        screen = self.game.screen; ox, oy = SCREEN_W//2-180, SCREEN_H//2-220; pw, ph = 360, 440
        pygame.draw.rect(screen, (40,42,65), (ox,oy,pw,ph), border_radius=8)
        pygame.draw.rect(screen, COL_UI_BORDER, (ox,oy,pw,ph), 2, border_radius=8)
        t = self.game.font_lg.render("Level Parameters", True, COL_UI_HL)
        screen.blit(t, (ox+pw//2-t.get_width()//2, oy+10))
        params = [("Name",self.level_name,None),("Total Lemmings",str(self.total_count),(5,100)),
                  ("Save Target",str(self.save_count),(1,self.total_count)),
                  ("Release Rate",str(self.release_rate),(5,120)),
                  ("Time Limit(s)",str(self.time_limit),(60,999))]
        skills = [Skill.BLOCKER,Skill.CLIMBER,Skill.FLOATER,Skill.BOMBER,
                  Skill.BUILDER,Skill.BASHER,Skill.MINER,Skill.DIGGER]
        y = oy + 50
        for i, item in enumerate(params):
            label, value = item[0], item[1]
            sel = (self.param_cursor == i)
            bg = COL_UI_SK_SEL if sel else (50,52,70)
            pygame.draw.rect(screen, bg, (ox+10,y,pw-20,26), border_radius=3)
            if sel: pygame.draw.rect(screen, COL_UI_HL, (ox+10,y,pw-20,26), 2, border_radius=3)
            t = self.game.font_sm.render(f"{label}:", True, COL_UI_TEXT); screen.blit(t, (ox+15, y+5))
            vt = self.game.font_sm.render(value, True, WHITE if sel else COL_UI_TEXT)
            screen.blit(vt, (ox+pw-30-vt.get_width(), y+5)); y += 30
        for j, sk in enumerate(skills):
            i = j + 5; sel = (self.param_cursor == i)
            bg = COL_UI_SK_SEL if sel else (50,52,70)
            pygame.draw.rect(screen, bg, (ox+10,y,pw-20,26), border_radius=3)
            if sel: pygame.draw.rect(screen, COL_UI_HL, (ox+10,y,pw-20,26), 2, border_radius=3)
            cnt = self.skill_counts.get(sk, 0)
            t = self.game.font_sm.render(f"{SKILL_NAMES[sk]}:", True, COL_UI_TEXT); screen.blit(t, (ox+15, y+5))
            vt = self.game.font_sm.render(f"x{cnt}", True, WHITE if sel else COL_UI_TEXT)
            screen.blit(vt, (ox+pw-30-vt.get_width(), y+5)); y += 30

    def _draw_file_dialog(self):
        screen = self.game.screen
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA); ov.fill((0,0,0,150)); screen.blit(ov, (0,0))
        ox, oy, pw, ph = SCREEN_W//2-180, SCREEN_H//2-150, 360, 300
        pygame.draw.rect(screen, (40,42,65), (ox,oy,pw,ph), border_radius=8)
        pygame.draw.rect(screen, COL_UI_BORDER, (ox,oy,pw,ph), 2, border_radius=8)
        if self.show_file_dialog == "save":
            t = self.game.font_lg.render("Save Level", True, COL_UI_HL)
            screen.blit(t, (ox+pw//2-t.get_width()//2, oy+10))
            pygame.draw.rect(screen, (50,52,70), (ox+20,oy+50,pw-40,28), border_radius=3)
            fn = self.file_name_input + ("_" if pygame.time.get_ticks()%1000<500 else "")
            t = self.game.font_sm.render(fn, True, WHITE); screen.blit(t, (ox+25, oy+56))
            t = self.game.font_sm.render("ENTER to save, ESC cancel", True, (150,150,170)); screen.blit(t, (ox+20,oy+90))
        elif self.show_file_dialog == "load":
            t = self.game.font_lg.render("Load Level", True, COL_UI_HL)
            screen.blit(t, (ox+pw//2-t.get_width()//2, oy+10))
            for i, fn in enumerate(self.file_list):
                fy = oy+50+i*28-self.file_scroll
                if fy < oy+40 or fy > oy+ph-10: continue
                sel = (i == self.file_selected)
                bg = COL_UI_SK_SEL if sel else (50,52,70)
                pygame.draw.rect(screen, bg, (ox+15,fy,pw-30,26), border_radius=3)
                t = self.game.font_sm.render(fn, True, WHITE if sel else COL_UI_TEXT); screen.blit(t, (ox+20,fy+5))
            t = self.game.font_sm.render("Click or ENTER to load, ESC cancel", True, (150,150,170)); screen.blit(t, (ox+20,oy+ph-30))
        elif self.show_file_dialog == "unsaved":
            t = self.game.font.render("Unsaved changes! Quit?", True, WHITE)
            screen.blit(t, (SCREEN_W//2-t.get_width()//2, SCREEN_H//2-20))
            cx = SCREEN_W//2
            pygame.draw.rect(screen, (50,150,50), (cx-100,SCREEN_H//2+20,80,30), border_radius=4)
            pygame.draw.rect(screen, (150,50,50), (cx+20,SCREEN_H//2+20,80,30), border_radius=4)
            t1 = self.game.font_sm.render("Yes", True, WHITE); t2 = self.game.font_sm.render("No", True, WHITE)
            screen.blit(t1, (cx-70, SCREEN_H//2+27)); screen.blit(t2, (cx+45, SCREEN_H//2+27))

class LemmingsGame:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Pygame Lemmings - Ultimate Edition (15 Levels)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 22)
        self.font_sm = pygame.font.SysFont(None, 17)
        self.font_lg = pygame.font.SysFont(None, 32)
        self.font_title = pygame.font.SysFont(None, 52)
        try:
            self.sounds = _gen_sounds()
        except Exception:
            self.sounds = None
        self.state = "menu"
        self.current_level = 1
        self.max_levels = 15
        self.high_scores = load_scores()
        self.custom_levels = []
        self.testing_from_editor = False
        self.test_play_data = None
        self.test_play_name = ""
        self.editor = None
        self.terrain = None
        self.lemmings = []
        self.particles = []
        self.fireworks = []
        self.pickups = []
        self.pickup_objs = []
        self.entrance = (200, 800)
        self.exit_pos = (1400, 800)
        self.total_lemmings = 20
        self.save_target = 10
        self.saved = 0
        self.died = 0
        self.released = 0
        self.release_timer = 0
        self.release_rate = 35
        self.game_timer = 0
        self.time_limit = 300
        self.selected_skill = Skill.NONE
        self.skill_counts = {}
        self.skill_rects = {}
        self.paused = False
        self.nuking = False
        self.speed = 1
        self.zoom = 1.0
        self.auto_camera = False
        self.show_minimap = True
        self.cam_x = 0.0; self.cam_y = 0.0
        self.world_w = 1600; self.world_h = 1200
        self.minimap_surf = None
        self.current_level_key = "1"
        self.result_timer = 0
        self.exit_rect = pygame.Rect(0, 0, 0, 0)
        self._scan_custom_levels()

    def _scan_custom_levels(self):
        self.custom_levels = []
        if os.path.isdir(LEVELS_DIR):
            for f in sorted(os.listdir(LEVELS_DIR)):
                if f.endswith('.json'):
                    path = os.path.join(LEVELS_DIR, f)
                    try:
                        with open(path, 'r') as fh:
                            d = json.load(fh)
                        self.custom_levels.append({
                            "path": path, "filename": f,
                            "name": d.get("name", f.replace('.json', ''))
                        })
                    except Exception:
                        pass

    def init_level(self, num):
        ld = create_level(num)
        self.init_level_from_data(ld, str(num))
        self.current_level = num
        self.current_level_key = str(num)

    def init_level_from_data(self, ld, key):
        self.terrain = Terrain(ld["terrain"], ld["world_w"], ld["world_h"])
        self.world_w = ld["world_w"]
        self.world_h = ld["world_h"]
        self.entrance = tuple(ld["entrance"])
        self.exit_pos = tuple(ld["exit_pos"])
        self.total_lemmings = ld["total_count"]
        self.save_target = ld["save_count"]
        self.release_rate = ld["release_rate"]
        self.time_limit = ld.get("time_limit", 300)
        self.skill_counts = dict(ld["skill_counts"])
        self.lemmings = []
        self.particles = []
        self.fireworks = []
        self.saved = 0
        self.died = 0
        self.released = 0
        self.release_timer = 0
        self.game_timer = 0
        self.paused = False
        self.nuking = False
        self.speed = 1
        self.selected_skill = Skill.NONE
        self.current_level_key = key
        # Pickups
        raw_pickups = ld.get("pickups", [])
        self.pickup_objs = [Pickup(p["x"], p["y"], p["type"]) for p in raw_pickups]
        self.exit_rect = pygame.Rect(self.exit_pos[0] - 12, self.exit_pos[1] - 18, 24, 36)
        self.cam_x = max(0, min(self.entrance[0] - GAME_W // 2, self.world_w - GAME_W))
        self.cam_y = max(0, min(self.entrance[1] - GAME_H // 2, self.world_h - GAME_H))
        self.minimap_surf = None

    def spawn_lemming(self):
        if self.released >= self.total_lemmings: return
        ex, ey = self.entrance
        self.lemmings.append(Lemming(ex, ey, 1))
        self.released += 1

    def assign_skill_at(self, mx, my):
        if self.selected_skill == Skill.NONE: return
        if self.skill_counts.get(self.selected_skill, 0) <= 0: return
        wx = int(mx / self.zoom) + self.cam_x
        wy = int(my / self.zoom) + self.cam_y
        best = None; best_d = 15
        for lem in self.lemmings:
            if not lem.alive: continue
            d = math.hypot(wx - lem.x, wy - (lem.y - 5))
            if d < best_d:
                best_d = d; best = lem
        if best and best.assign_skill(self.selected_skill, self.sounds):
            # Permanent skills don't cost from pool
            if self.selected_skill not in (Skill.CLIMBER, Skill.FLOATER):
                self.skill_counts[self.selected_skill] -= 1
            for _ in range(6):
                self.particles.append(Particle(best.x, best.y - 5,
                    random.uniform(-2, 2), random.uniform(-3, 0), (255, 255, 100), 20, 3))

    def check_blockers(self):
        for lem in self.lemmings:
            if not lem.alive or lem.state != LState.BLOCKING: continue
            bx, by = int(lem.x), int(lem.y)
            for o in self.lemmings:
                if o is lem or not o.alive or o.state != LState.WALKING: continue
                if abs(bx - int(o.x)) < 8 and abs(by - int(o.y)) < 12:
                    o.direction *= -1

    def update_camera(self):
        if self.auto_camera:
            alive = [l for l in self.lemmings if l.alive and not l.exited]
            if alive:
                ax = sum(l.x for l in alive) / len(alive)
                ay = sum(l.y for l in alive) / len(alive)
                tcx = ax - GAME_W / (2 * self.zoom)
                tcy = ay - GAME_H / (2 * self.zoom)
                self.cam_x += (tcx - self.cam_x) * 0.08
                self.cam_y += (tcy - self.cam_y) * 0.08
                self._clamp_camera()
            return
        keys = pygame.key.get_pressed()
        spd = 8
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:  self.cam_x -= spd
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.cam_x += spd
        if keys[pygame.K_UP] or keys[pygame.K_w]:    self.cam_y -= spd
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:  self.cam_y += spd
        mx, my = pygame.mouse.get_pos()
        if mx < 20: self.cam_x -= spd
        elif mx > GAME_W - 20 and mx < GAME_W: self.cam_x += spd
        if my < 20: self.cam_y -= spd
        elif my > GAME_H - 20: self.cam_y += spd
        self._clamp_camera()

    def _clamp_camera(self):
        vw = int(GAME_W / self.zoom)
        vh = int(GAME_H / self.zoom)
        self.cam_x = max(0, min(self.cam_x, self.world_w - vw))
        self.cam_y = max(0, min(self.cam_y, self.world_h - vh))

    def update(self):
        if self.paused: return
        for _ in range(self.speed):
            self.game_timer += 1
            # Time limit check
            time_secs = self.game_timer // 60
            if time_secs >= self.time_limit and self.time_limit > 0:
                # Time's up - nuke remaining
                self.nuking = True
            if not self.nuking:
                self.release_timer += 1
                if self.release_timer >= self.release_rate and self.released < self.total_lemmings:
                    self.spawn_lemming(); self.release_timer = 0
            else:
                for lem in self.lemmings:
                    if lem.alive and lem.state not in (LState.EXPLODING, LState.EXITING):
                        lem.state = LState.EXPLODING; lem.bomb_timer = random.randint(10, 60)
                self.nuking = False
                if self.sounds: self.sounds["nuke"].play()

            for lem in self.lemmings:
                if not lem.alive: continue
                old = lem.state
                pickup = lem.update(self.terrain, self.sounds, self.pickup_objs)
                # Process pickup
                if pickup and not pickup.collected:
                    sk_map = {"builder": Skill.BUILDER, "bomber": Skill.BOMBER, "digger": Skill.DIGGER,
                              "basher": Skill.BASHER, "miner": Skill.MINER, "floater": Skill.FLOATER,
                              "climber": Skill.CLIMBER, "blocker": Skill.BLOCKER}
                    sk = sk_map.get(pickup.type)
                    if sk:
                        self.skill_counts[sk] = self.skill_counts.get(sk, 0) + 1
                    for _ in range(10):
                        self.particles.append(Particle(pickup.x, pickup.y,
                            random.uniform(-2, 2), random.uniform(-3, 0), COL_PICKUP, 25, 2))
                if lem.state == LState.WALKING:
                    lx, ly = int(lem.x), int(lem.y)
                    if self.exit_rect.collidepoint(lx, ly - 5):
                        lem.state = LState.EXITING; lem.exit_timer = 30
                if not lem.alive:
                    if lem.exited:
                        self.saved += 1
                        if self.sounds: self.sounds["ding"].play()
                    else:
                        self.died += 1
                    if old == LState.EXPLODING:
                        for _ in range(20):
                            self.particles.append(Particle(lem.x, lem.y - 5,
                                random.uniform(-4, 4), random.uniform(-5, 1),
                                random.choice([(255,200,50),(255,100,0),(255,50,0)]),
                                random.randint(15, 45), 3))
                    if old in (LState.BASHING, LState.MINING, LState.DIGGING):
                        for _ in range(3):
                            self.particles.append(Particle(lem.x, lem.y,
                                random.uniform(-1, 1), random.uniform(-2, 0),
                                random.choice(COL_DIRT), random.randint(10, 25), 2))

            self.check_blockers()
            self.particles = [p for p in self.particles if p.update()]

            active = sum(1 for l in self.lemmings if l.alive)
            if self.released >= self.total_lemmings and active == 0:
                prev = self.high_scores.get(self.current_level_key, 0)
                if self.saved > prev:
                    self.high_scores[self.current_level_key] = self.saved
                    save_scores(self.high_scores)
                if self.saved >= self.save_target:
                    self.state = "win"; self.result_timer = 0
                    if self.sounds: self.sounds["fanfare"].play()
                else:
                    self.state = "lose"; self.result_timer = 0

        self.update_camera()

    def draw_entrance(self, cx, cy):
        ex, ey = self.entrance
        ex = int((ex - cx) * self.zoom)
        ey = int((ey - cy) * self.zoom)
        if ex < -30 or ex > GAME_W + 30: return
        pygame.draw.rect(self.screen, (80, 80, 80), (ex - 18, ey - 22, 36, 6))
        pygame.draw.rect(self.screen, (100, 100, 100), (ex - 15, ey - 22, 30, 4))
        off = 0 if self.released < self.total_lemmings else 18
        pygame.draw.rect(self.screen, COL_ENTRANCE, (ex - 12, ey - 18 + off, 24, 18 - off))
        ay = ey - 28 + int(3 * math.sin(self.game_timer * 0.08))
        pygame.draw.polygon(self.screen, (200, 255, 200), [(ex, ay + 6), (ex - 4, ay), (ex + 4, ay)])

    def draw_exit(self, cx, cy):
        ex, ey = self.exit_pos
        ex = int((ex - cx) * self.zoom)
        ey = int((ey - cy) * self.zoom)
        if ex < -30 or ex > GAME_W + 30: return
        pygame.draw.rect(self.screen, (140, 40, 40), (ex - 14, ey - 18, 28, 36))
        pygame.draw.arc(self.screen, (200, 70, 70), (ex - 14, ey - 26, 28, 18), 0, math.pi, 3)
        glow = int(20 * abs(math.sin(self.game_timer * 0.06)))
        pygame.draw.rect(self.screen, (255, glow, glow), (ex - 14, ey - 18, 28, 36), 2)
        ay = ey - 30 + int(3 * math.sin(self.game_timer * 0.06))
        pygame.draw.polygon(self.screen, COL_UI_HL, [(ex, ay + 8), (ex - 5, ay), (ex + 5, ay)])

    def draw_minimap(self):
        if not self.show_minimap: return
        if self.minimap_surf is None:
            self.minimap_surf = self.terrain.render_minimap(120)
        mm = self.minimap_surf
        mx_pos, my_pos = GAME_W - 130, 5
        pygame.draw.rect(self.screen, (0, 0, 0), (mx_pos - 2, my_pos - 2, 124, 124))
        self.screen.blit(mm, (mx_pos, my_pos))
        sx = self.cam_x / self.world_w * 120
        sy = self.cam_y / self.world_h * 120
        sw = (GAME_W / self.zoom) / self.world_w * 120
        sh = (GAME_H / self.zoom) / self.world_h * 120
        pygame.draw.rect(self.screen, WHITE, (mx_pos + sx, my_pos + sy, sw, sh), 1)
        enx = self.entrance[0] / self.world_w * 120 + mx_pos
        eny = self.entrance[1] / self.world_h * 120 + my_pos
        pygame.draw.circle(self.screen, COL_ENTRANCE, (int(enx), int(eny)), 3)
        exx = self.exit_pos[0] / self.world_w * 120 + mx_pos
        exy = self.exit_pos[1] / self.world_h * 120 + my_pos
        pygame.draw.circle(self.screen, COL_EXIT, (int(exx), int(exy)), 3)
        for lem in self.lemmings:
            if not lem.alive: continue
            lx = lem.x / self.world_w * 120 + mx_pos
            ly = lem.y / self.world_h * 120 + my_pos
            pygame.draw.circle(self.screen, (255, 255, 0), (int(lx), int(ly)), 1)
        # Pickup dots
        for p in self.pickup_objs:
            if not p.collected:
                px = p.x / self.world_w * 120 + mx_pos
                py = p.y / self.world_h * 120 + my_pos
                pygame.draw.circle(self.screen, COL_PICKUP, (int(px), int(py)), 2)

    def draw_timer_bar(self):
        if self.time_limit <= 0: return
        time_secs = self.game_timer // 60
        remaining = max(0, self.time_limit - time_secs)
        pct = remaining / self.time_limit
        bar_w = GAME_W - 10
        bar_h = 6
        bar_y = GAME_H - 10
        pygame.draw.rect(self.screen, (40, 40, 40), (5, bar_y, bar_w, bar_h), border_radius=3)
        # Color based on remaining time
        if pct > 0.5: color = (50, 200, 50)
        elif pct > 0.25: color = (200, 200, 50)
        else: color = (200, 50, 50)
        pygame.draw.rect(self.screen, color, (5, bar_y, int(bar_w * pct), bar_h), border_radius=3)
        # Time text
        mins = remaining // 60; secs = remaining % 60
        t = self.font_sm.render(f"{mins}:{secs:02d}", True, WHITE)
        self.screen.blit(t, (8, bar_y - 14))
        # Flashing warning
        if pct < 0.15 and (self.game_timer // 30) % 2 == 0:
            wt = self.font_sm.render("LOW TIME!", True, (255, 50, 50))
            self.screen.blit(wt, (60, bar_y - 14))

    def draw_progress_bar(self):
        """Draw saved/target progress bar in game area."""
        bar_w = 200
        bar_h = 8
        bx = GAME_W // 2 - bar_w // 2
        by = 4
        pct = self.saved / max(1, self.save_target)
        pygame.draw.rect(self.screen, (30, 30, 50), (bx - 1, by - 1, bar_w + 2, bar_h + 2), border_radius=4)
        # Background
        pygame.draw.rect(self.screen, (50, 50, 70), (bx, by, bar_w, bar_h), border_radius=3)
        # Fill
        fill_color = (50, 200, 50) if pct >= 1.0 else (200, 200, 50) if pct >= 0.5 else (200, 100, 50)
        if pct > 0:
            pygame.draw.rect(self.screen, fill_color, (bx, by, int(bar_w * min(1.0, pct)), bar_h), border_radius=3)
        # Text
        txt = f"{self.saved}/{self.save_target}"
        t = self.font_sm.render(txt, True, WHITE)
        self.screen.blit(t, (bx + bar_w + 5, by - 2))

    def draw_ui(self):
        pygame.draw.rect(self.screen, COL_UI_BG, (UI_X, 0, UI_W, SCREEN_H))
        pygame.draw.line(self.screen, COL_UI_BORDER, (UI_X, 0), (UI_X, SCREEN_H), 2)
        x = UI_X + 6; y = 6
        def txt(s, c=COL_UI_TEXT, f=None):
            nonlocal y
            if f is None: f = self.font
            t = f.render(s, True, c); self.screen.blit(t, (x, y)); y += t.get_height() + 2

        lvl_label = self.current_level_key
        if self.testing_from_editor:
            lvl_label = f"Test"
        txt(f"Lvl {lvl_label}", COL_UI_HL)
        secs = self.game_timer // 60; txt(f"Time: {secs // 60}:{secs % 60:02d}")
        y += 2

        active = sum(1 for l in self.lemmings if l.alive and not l.exited)
        txt(f"Out: {self.released}/{self.total_lemmings}")
        txt(f"Active: {active}")
        col = COL_UI_HL if self.saved >= self.save_target else (255, 100, 100)
        txt(f"Saved: {self.saved}/{self.save_target}", col)
        txt(f"Died: {self.died}", (255, 100, 100))
        pct = (self.saved / max(1, self.released)) * 100 if self.released > 0 else 0
        txt(f"Rate: {pct:.0f}%")
        y += 2

        if self.released > 0:
            if pct >= 90: rating, rc = "GOLD", GOLD
            elif pct >= 70: rating, rc = "SILVER", SILVER
            elif pct >= 50: rating, rc = "BRONZE", BRONZE
            else: rating, rc = "---", (100, 100, 100)
            txt(f"Rating: {rating}", rc)
        y += 2

        # Pickups remaining
        remaining_pickups = sum(1 for p in self.pickup_objs if not p.collected)
        if remaining_pickups > 0:
            txt(f"Pickups: {remaining_pickups}", COL_PICKUP, self.font_sm)
        y += 2

        txt(f"Release: {self.release_rate}f", COL_UI_TEXT, self.font_sm)
        txt(f"Speed: {self.speed}x", COL_UI_HL if self.speed > 1 else COL_UI_TEXT, self.font_sm)
        txt(f"Zoom: {self.zoom}x", COL_UI_HL if self.zoom < 1.0 else COL_UI_TEXT, self.font_sm)
        if self.auto_camera:
            txt("AUTO-CAM", (100, 255, 100), self.font_sm)
        y += 2

        txt("+/- rate  F speed  M map", (120, 120, 150), self.font_sm)
        txt("Z zoom  C auto-cam", (120, 120, 150), self.font_sm)
        y += 4

        pygame.draw.line(self.screen, COL_UI_BORDER, (x, y), (UI_X + UI_W - 6, y)); y += 6

        txt("Skills:", COL_UI_HL)
        self.skill_rects = {}
        skills = [Skill.BLOCKER, Skill.CLIMBER, Skill.FLOATER, Skill.BOMBER,
                  Skill.BUILDER, Skill.BASHER, Skill.MINER, Skill.DIGGER]
        for skill in skills:
            cnt = self.skill_counts.get(skill, 0)
            sel = (self.selected_skill == skill)
            hk = SKILL_HOTKEYS.get(skill, "")
            rect = pygame.Rect(x, y, UI_W - 12, 22)
            self.skill_rects[skill] = rect
            if sel:
                pygame.draw.rect(self.screen, COL_UI_SK_SEL, rect, border_radius=3)
                pygame.draw.rect(self.screen, COL_UI_HL, rect, 2, border_radius=3)
            else:
                c = COL_UI_SK if cnt > 0 else (35, 35, 48)
                pygame.draw.rect(self.screen, c, rect, border_radius=3)
                pygame.draw.rect(self.screen, (70, 70, 90), rect, 1, border_radius=3)
            cc = WHITE if cnt > 0 else (80, 80, 80)
            t = self.font_sm.render(f"{hk}:{SKILL_NAMES[skill]}", True, cc)
            self.screen.blit(t, (x + 3, y + 4))
            t2 = self.font_sm.render(f"x{cnt}", True, cc)
            self.screen.blit(t2, (x + UI_W - 38, y + 4))
            y += 24

        y += 4
        pygame.draw.line(self.screen, COL_UI_BORDER, (x, y), (UI_X + UI_W - 6, y)); y += 4

        controls = [
            "LClick: Assign skill",
            "RClick: Deselect",
            "Arrows/WASD: Scroll",
            "N: Nuke  R: Restart",
            "P/Space: Pause  Esc: Menu",
            "F: Fast-fwd  M: Minimap",
            "Z: Zoom  C: Auto-cam",
        ]
        for c in controls:
            t = self.font_sm.render(c, True, (110, 110, 135))
            self.screen.blit(t, (x, y)); y += 12

        if self.paused:
            ps = pygame.Surface((GAME_W, 40), pygame.SRCALPHA)
            ps.fill((0, 0, 0, 160))
            self.screen.blit(ps, (0, GAME_H // 2 - 20))
            t = self.font_lg.render("|| PAUSED ||", True, WHITE)
            self.screen.blit(t, t.get_rect(center=(GAME_W // 2, GAME_H // 2)))

    def draw_menu(self):
        self.screen.fill((15, 15, 35))
        t = pygame.time.get_ticks()
        random.seed(42)
        for _ in range(60):
            sx = random.randint(0, SCREEN_W); sy = random.randint(0, SCREEN_H)
            brightness = int(80 + 60 * math.sin(t * 0.001 + sx * 0.1))
            pygame.draw.circle(self.screen, (brightness, brightness, brightness + 30), (sx, sy), 1)
        random.seed()

        shadow = self.font_title.render("PYGAME LEMMINGS", True, (30, 30, 60))
        title = self.font_title.render("PYGAME LEMMINGS", True, (80, 255, 80))
        self.screen.blit(shadow, shadow.get_rect(center=(SCREEN_W // 2 + 2, 52)))
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, 50)))
        sub = self.font.render("Ultimate Edition - 15 Levels + Editor", True, (180, 200, 255))
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_W // 2, 80)))

        # Animated lemmings
        for i in range(10):
            lx = 80 + i * 88 + int(15 * math.sin(t * 0.002 + i))
            ly = 125 + int(6 * math.sin(t * 0.004 + i * 1.5))
            pygame.draw.circle(self.screen, COL_LR, (lx, ly - 9), 4)
            pygame.draw.rect(self.screen, COL_LB, (lx - 3, ly - 6, 6, 7))
            lo = int(3 * math.sin(t * 0.006 + i * 2))
            pygame.draw.line(self.screen, COL_LB, (lx + 1, ly + 1), (lx + 1 + lo, ly + 5), 2)
            pygame.draw.line(self.screen, COL_LB, (lx - 1, ly + 1), (lx - 1 - lo, ly + 5), 2)

        pygame.draw.rect(self.screen, COL_GRASS[0], (40, 140, SCREEN_W - 80, 4))
        pygame.draw.rect(self.screen, COL_DIRT[0], (40, 144, SCREEN_W - 80, 20))

        y = 175
        lines = [
            ("Guide lemmings to the red exit by assigning them skills!", COL_UI_TEXT, self.font),
            ("", None, None),
            ("ENTER  Start game          ESC  Quit", COL_UI_HL, self.font),
            ("L  Level select            E  Level Editor", COL_UI_HL, self.font),
            ("", None, None),
            ("SKILLS (keys 1-8)", (200, 200, 220), self.font),
            ("Blocker  Climber  Floater  Bomber  Builder  Basher  Miner  Digger", (150, 155, 175), self.font_sm),
            ("", None, None),
            ("ULTIMATE EDITION FEATURES", GOLD, self.font),
            ("15 levels | Pickups for extra skills | Time limits", (170, 170, 195), self.font_sm),
            ("One-way tiles | Terrain decorations | Fill/Line editor tools", (170, 170, 195), self.font_sm),
            ("Permanent Climber/Floater | Timer bar | Progress bar", (170, 170, 195), self.font_sm),
            ("Level Editor: Save/Load, Mirror, Templates, Undo/Redo", (170, 170, 195), self.font_sm),
            ("Sound FX | Gold/Silver/Bronze | Minimap | Fireworks", (170, 170, 195), self.font_sm),
        ]
        for text, col, f in lines:
            if not text: y += 5; continue
            r = f.render(text, True, col)
            self.screen.blit(r, r.get_rect(center=(SCREEN_W // 2, y)))
            y += r.get_height() + 3

    def _get_all_level_keys(self):
        levels = []
        for i in range(1, self.max_levels + 1):
            ld = create_level(i)
            tl = ld.get("time_limit", 300)
            levels.append((str(i), f"Level {i}", LEVEL_DESCS.get(i, ""),
                          ld["total_count"], ld["save_count"], tl))
        for cl in self.custom_levels:
            try:
                with open(cl["path"], 'r') as f:
                    data = json.load(f)
                key = f"custom/{cl['filename']}"
                levels.append((key, cl["name"], f"Custom: {cl['filename']}",
                              data.get("total_count", 20), data.get("save_count", 10),
                              data.get("time_limit", 300)))
            except Exception:
                pass
        return levels

    def draw_level_select(self):
        self.screen.fill((20, 20, 45))
        t = self.font_lg.render("SELECT LEVEL", True, COL_UI_HL)
        self.screen.blit(t, t.get_rect(center=(SCREEN_W // 2, 30)))
        all_levels = self._get_all_level_keys()
        mx, my = pygame.mouse.get_pos()
        cols = 3
        # Scrollable
        scroll = getattr(self, '_ls_scroll', 0)
        for i_ev in [pygame.MOUSEWHEEL]:
            pass
        visible_per_col = 4
        total_rows = (len(all_levels) + cols - 1) // cols

        for idx, (key, label, desc, total, save_target, tl) in enumerate(all_levels):
            col = idx % cols
            row = idx // cols
            if row < scroll or row >= scroll + visible_per_col:
                continue
            bx = 80 + col * 320; by = 65 + (row - scroll) * 140
            bw, bh = 290, 130
            is_hover = bx <= mx <= bx + bw and by <= my <= by + bh
            bc = COL_UI_SK_SEL if is_hover else COL_UI_SK
            pygame.draw.rect(self.screen, bc, (bx, by, bw, bh), border_radius=8)
            pygame.draw.rect(self.screen, COL_UI_BORDER, (bx, by, bw, bh), 2, border_radius=8)
            nt = self.font_lg.render(label, True, WHITE)
            self.screen.blit(nt, (bx + 12, by + 6))
            dt = self.font_sm.render(desc, True, (180, 180, 200))
            self.screen.blit(dt, (bx + 12, by + 32))
            hs = self.high_scores.get(key, 0)
            ht = self.font_sm.render(f"Best: {hs}/{total}  Target: {save_target}  Time: {tl}s", True,
                                     GOLD if hs >= save_target else (150, 150, 170))
            self.screen.blit(ht, (bx + 12, by + 52))
            if hs > 0:
                p = (hs / max(1, total)) * 100
                if p >= 90: rt, rc = "GOLD", GOLD
                elif p >= 70: rt, rc = "SILVER", SILVER
                elif p >= 50: rt, rc = "BRONZE", BRONZE
                else: rt, rc = "---", (100, 100, 100)
                rtxt = self.font.render(rt, True, rc)
                self.screen.blit(rtxt, (bx + 12, by + 72))
            # Completed checkmark
            if hs >= save_target:
                ct = self.font_lg.render("[OK]", True, (50, 255, 50))
                self.screen.blit(ct, (bx + bw - 55, by + 8))

        it = self.font.render("Click level  |  Scroll: Mouse Wheel  |  ESC/ENTER: Back", True, (140, 140, 165))
        self.screen.blit(it, it.get_rect(center=(SCREEN_W // 2, SCREEN_H - 20)))
        # Store for event handling
        self._ls_data = (all_levels, cols, visible_per_col, scroll)

    def draw_result(self):
        cx, cy = self.cam_x, self.cam_y
        self.terrain.render(self.screen, cx, cy, self.zoom)
        self.draw_entrance(cx, cy)
        self.draw_exit(cx, cy)
        for p in self.pickup_objs: p.draw(self.screen, cx, cy, self.zoom, self.game_timer)
        for p in self.particles: p.draw(self.screen, cx, cy, self.zoom)
        for lem in self.lemmings: lem.draw(self.screen, cx, cy, self.zoom)
        for fw in self.fireworks: fw.draw(self.screen, cx, cy, self.zoom)

        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        self.screen.blit(ov, (0, 0))

        time_secs = self.game_timer // 60
        if self.state == "win":
            t = self.font_lg.render(f"LEVEL COMPLETE!", True, (80, 255, 80))
            self.screen.blit(t, t.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 100)))
            pct = (self.saved / max(1, self.total_lemmings)) * 100
            t2 = self.font.render(f"Saved: {self.saved}/{self.total_lemmings} ({pct:.0f}%)  Time: {time_secs // 60}:{time_secs % 60:02d}", True, WHITE)
            self.screen.blit(t2, t2.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 60)))
            if pct >= 90: rt, rc = "*** GOLD ***", GOLD
            elif pct >= 70: rt, rc = "** SILVER **", SILVER
            elif pct >= 50: rt, rc = "* BRONZE *", BRONZE
            else: rt, rc = "Completed", (180, 180, 180)
            t3 = self.font_lg.render(rt, True, rc)
            self.screen.blit(t3, t3.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 20)))
            # Stats
            collected = sum(1 for p in self.pickup_objs if p.collected)
            if collected > 0:
                t4 = self.font_sm.render(f"Pickups collected: {collected}/{len(self.pickup_objs)}", True, COL_PICKUP)
                self.screen.blit(t4, t4.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 15)))
            if self.testing_from_editor:
                msg = "ENTER: Back to Editor  |  R: Replay  |  ESC: Editor"
            else:
                msg = "ENTER: Next level  |  R: Replay  |  ESC: Menu"
            t5 = self.font.render(msg, True, COL_UI_HL)
            self.screen.blit(t5, t5.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 55)))
        else:
            t = self.font_lg.render("LEVEL FAILED", True, (255, 80, 80))
            self.screen.blit(t, t.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 70)))
            t2 = self.font.render(f"Saved {self.saved}, needed {self.save_target}  Time: {time_secs // 60}:{time_secs % 60:02d}", True, WHITE)
            self.screen.blit(t2, t2.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 30)))
            if self.testing_from_editor:
                msg = "R: Retry  |  ENTER: Editor  |  ESC: Editor"
            else:
                msg = "R: Retry  |  ENTER: Menu  |  ESC: Menu"
            t3 = self.font.render(msg, True, COL_UI_HL)
            self.screen.blit(t3, t3.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 20)))

    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: return False
            if ev.type == pygame.KEYDOWN:
                if self.state == "menu":
                    if ev.key == pygame.K_RETURN:
                        self.testing_from_editor = False
                        self.state = "playing"; self.init_level(self.current_level)
                    elif ev.key == pygame.K_l:
                        self._scan_custom_levels()
                        self._ls_scroll = 0
                        self.state = "level_select"
                    elif ev.key == pygame.K_e:
                        self.state = "editor"
                        self.editor = LevelEditor(self)
                    elif ev.key in (pygame.K_1, pygame.K_2, pygame.K_3,
                                    pygame.K_4, pygame.K_5, pygame.K_6,
                                    pygame.K_7, pygame.K_8, pygame.K_9):
                        num = ev.key - pygame.K_0
                        if num <= self.max_levels:
                            self.current_level = num
                            self.testing_from_editor = False
                            self.state = "playing"; self.init_level(self.current_level)
                    elif ev.key == pygame.K_ESCAPE: return False

                elif self.state == "level_select":
                    if ev.key == pygame.K_ESCAPE or ev.key == pygame.K_RETURN:
                        self.state = "menu"
                    elif ev.key in (pygame.K_1, pygame.K_2, pygame.K_3,
                                    pygame.K_4, pygame.K_5, pygame.K_6,
                                    pygame.K_7, pygame.K_8, pygame.K_9):
                        num = ev.key - pygame.K_0
                        if num <= self.max_levels:
                            self.current_level = num
                            self.testing_from_editor = False
                            self.state = "playing"; self.init_level(self.current_level)

                elif self.state == "playing":
                    if ev.key == pygame.K_ESCAPE:
                        if self.testing_from_editor:
                            self.state = "editor"
                        else:
                            self.state = "menu"
                    elif ev.key in SKILL_KEYS:
                        sk = SKILL_KEYS[ev.key]
                        self.selected_skill = sk if self.selected_skill != sk else Skill.NONE
                    elif ev.key in (pygame.K_p, pygame.K_SPACE): self.paused = not self.paused
                    elif ev.key == pygame.K_r:
                        if self.testing_from_editor and self.test_play_data:
                            self.init_level_from_data(self.test_play_data, self.test_play_name)
                        else:
                            self.init_level(self.current_level)
                        self.state = "playing"
                    elif ev.key == pygame.K_n: self.nuking = True
                    elif ev.key == pygame.K_f:
                        self.speed = self.speed % 3 + 1
                    elif ev.key == pygame.K_m:
                        self.show_minimap = not self.show_minimap
                    elif ev.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        self.release_rate = max(5, self.release_rate - 5)
                    elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self.release_rate = min(120, self.release_rate + 5)
                    elif ev.key == pygame.K_z:
                        self.zoom = 0.5 if self.zoom == 1.0 else 1.0
                        self._clamp_camera()
                    elif ev.key == pygame.K_c:
                        self.auto_camera = not self.auto_camera

                elif self.state in ("win", "lose"):
                    if ev.key == pygame.K_RETURN:
                        if self.testing_from_editor:
                            self.state = "editor"
                        elif self.state == "win":
                            try:
                                cur = int(self.current_level_key)
                                if cur < self.max_levels:
                                    self.current_level = cur + 1
                                    self.init_level(self.current_level); self.state = "playing"
                                else:
                                    self.state = "menu"
                            except ValueError:
                                self.state = "menu"
                        else:
                            self.state = "menu"
                    elif ev.key == pygame.K_r:
                        if self.testing_from_editor and self.test_play_data:
                            self.init_level_from_data(self.test_play_data, self.test_play_name)
                        else:
                            self.init_level(self.current_level)
                        self.state = "playing"
                    elif ev.key == pygame.K_ESCAPE:
                        self.state = "editor" if self.testing_from_editor else "menu"

            if ev.type == pygame.MOUSEWHEEL and self.state == "level_select":
                scroll = getattr(self, '_ls_scroll', 0)
                scroll = max(0, scroll - ev.y)
                self._ls_scroll = scroll

            if ev.type == pygame.MOUSEBUTTONDOWN:
                if self.state == "menu":
                    if ev.button == 1:
                        self.testing_from_editor = False
                        self.state = "playing"; self.init_level(self.current_level)

                elif self.state == "level_select":
                    if ev.button == 1:
                        mx, my = ev.pos
                        ls_data = getattr(self, '_ls_data', None)
                        if ls_data:
                            all_levels, cols, vis, scroll = ls_data
                            for idx, (key, label, desc, total, save_target, tl) in enumerate(all_levels):
                                row = idx // cols
                                if row < scroll or row >= scroll + vis: continue
                                c = idx % cols
                                bx = 80 + c * 320; by = 65 + (row - scroll) * 140
                                if bx <= mx <= bx + 290 and by <= my <= by + 130:
                                    try:
                                        num = int(key)
                                        self.current_level = num
                                        self.testing_from_editor = False
                                        self.init_level(self.current_level)
                                        self.state = "playing"
                                    except ValueError:
                                        self._load_custom_level(key)
                                    break

                elif self.state == "playing":
                    mx, my = ev.pos
                    if ev.button == 1:
                        if mx < GAME_W:
                            self.assign_skill_at(mx, my)
                        else:
                            for sk, rect in self.skill_rects.items():
                                if rect.collidepoint(mx, my):
                                    self.selected_skill = sk if self.selected_skill != sk else Skill.NONE
                                    break
                    elif ev.button == 3:
                        self.selected_skill = Skill.NONE
        return True

    def _load_custom_level(self, key):
        filename = key.split("/", 1)[1] if "/" in key else key
        path = os.path.join(LEVELS_DIR, filename)
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            terrain_bytes = bytearray(base64.b64decode(data["terrain_b64"]))
            sc_raw = data.get("skill_counts", {})
            skill_counts = {int(k): v for k, v in sc_raw.items()}
            for s in [Skill.BLOCKER, Skill.CLIMBER, Skill.FLOATER, Skill.BOMBER,
                      Skill.BUILDER, Skill.BASHER, Skill.MINER, Skill.DIGGER]:
                if s not in skill_counts:
                    skill_counts[s] = 0
            ld = {
                "terrain": terrain_bytes, "world_w": data["world_w"], "world_h": data["world_h"],
                "entrance": data["entrance"], "exit_pos": data["exit_pos"],
                "save_count": data.get("save_count", 10), "total_count": data.get("total_count", 20),
                "release_rate": data.get("release_rate", 35),
                "time_limit": data.get("time_limit", 300),
                "skill_counts": skill_counts, "pickups": [],
            }
            self.testing_from_editor = False
            self.init_level_from_data(ld, key)
            self.state = "playing"
        except Exception:
            pass

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "level_select":
            self.draw_level_select()
        elif self.state == "editor":
            self.editor.draw()
        elif self.state == "playing":
            cx, cy = self.cam_x, self.cam_y
            self.terrain.render(self.screen, cx, cy, self.zoom)
            self.draw_entrance(cx, cy)
            self.draw_exit(cx, cy)
            for p in self.pickup_objs: p.draw(self.screen, cx, cy, self.zoom, self.game_timer)
            for p in self.particles: p.draw(self.screen, cx, cy, self.zoom)
            for lem in self.lemmings: lem.draw(self.screen, cx, cy, self.zoom)
            mx, my = pygame.mouse.get_pos()
            if mx < GAME_W and self.selected_skill != Skill.NONE:
                pygame.draw.circle(self.screen, COL_UI_HL, (mx, my), 10, 1)
                t = self.font_sm.render(SKILL_NAMES.get(self.selected_skill, ""), True, COL_UI_HL)
                self.screen.blit(t, (mx + 12, my - 8))
            self.draw_minimap()
            self.draw_timer_bar()
            self.draw_progress_bar()
            self.draw_ui()
            if self.speed > 1:
                st = self.font_sm.render(f"{self.speed}x", True, (255, 200, 50))
                self.screen.blit(st, (5, 5))
            if self.zoom < 1.0:
                zt = self.font_sm.render(f"{self.zoom}x", True, (200, 200, 255))
                self.screen.blit(zt, (30, 5))
            if self.auto_camera:
                at = self.font_sm.render("AUTO", True, (100, 255, 100))
                self.screen.blit(at, (5, 18))
        elif self.state in ("win", "lose"):
            self.result_timer += 1
            if self.state == "win" and self.result_timer % 15 == 0:
                fx = random.randint(100, GAME_W - 100)
                fy = random.randint(50, GAME_H // 2)
                self.fireworks.append(Firework(fx + self.cam_x, fy + self.cam_y))
            self.fireworks = [fw for fw in self.fireworks if fw.update()]
            self.draw_result()

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            if self.state == "editor":
                running = self.editor.handle_events()
                self.editor.update()
            else:
                running = self.handle_events()
                if self.state == "playing":
                    self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit(); sys.exit()


if __name__ == "__main__":
    game = LemmingsGame()
    game.run()
