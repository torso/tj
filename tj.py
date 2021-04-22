from array import array
from random import (random,randint)
import math
import tkinter

TILE_WIDTH = 16
TILE_HEIGHT = 16

LEVEL_WIDTH_TILES = 40*8
LEVEL_HEIGHT_TILES = 30*8
LEVEL_WIDTH = LEVEL_WIDTH_TILES * TILE_WIDTH
LEVEL_HEIGHT = LEVEL_HEIGHT_TILES * TILE_HEIGHT

VIEWPORT_WIDTH = 640
VIEWPORT_HEIGHT = 480

GRAVITY = -.2

TILE_TYPE_SPACE = 0
TILE_TYPE_GRASS = 1
TILE_TYPE_WATER = 2

tileColors = ['black', 'green', 'blue']


# Returns True if the circle with center at (cx,cy) and radius cr contains the point (px,py)
def circleContainsPoint(cx, cy, cr, px, py):
    dx = cx - px
    dy = cy - py
    return dx*dx + dy*dy < cr*cr

# (x,y,z) is the bottom center of cylinder. (x,y+height,z) is top center of cylinder.
def cylindersIntersect(x1, y1, z1, radius1, height1, x2, y2, z2, radius2, height2):
    return circleContainsPoint(x1, z1, radius1 + radius2, x2, z2) and \
        y1 < y2 + height2 and y1 + height1 > y2


class RectXZ:
    def __init__(self, x1, z1, x2, z2):
        self.x1 = x1
        self.z1 = z1
        self.x2 = x2
        self.z2 = z2

    def __repr__(self):
        return 'RectXZ(x1:{}, z1:{}, x2:{}, z2:{})'.format(self.x1, self.z1, self.x2, self.z2)

    def contains(self, x, z):
        return self.x1 <= x < self.x2 and self.z1 <= z < self.z2

    def intersects(self, rect):
        return self.x1 < rect.x2 and self.x2 > rect.x1 and self.z1 < rect.z2 and self.z2 > rect.z1

    def intersectsOrTouches(self, rect):
        return self.x1 <= rect.x2 and self.x2 >= rect.x1 and self.z1 <= rect.z2 and self.z2 >= rect.z1


class Input:
    def __init__(self):
        self.update({}, {})

    def update(self, held, pressed):
        self.left   = held.get('A', False) or held.get('a', False) or held.get('Left',  False) or held.get('KP_Left',  False)
        self.right  = held.get('D', False) or held.get('d', False) or held.get('Right', False) or held.get('KP_Right', False)
        self.up     = held.get('W', False) or held.get('w', False) or held.get('Up',    False) or held.get('KP_Up',    False)
        self.down   = held.get('S', False) or held.get('s', False) or held.get('Down',  False) or held.get('KP_Down',  False)
        self.action = pressed.get('Control_L', False) or pressed.get('Control_R', False)
        self.map    = pressed.get('Q',         False) or pressed.get('q',         False)
        self.pause  = pressed.get('space',     False)
        # debug
        self.newMap = pressed.get('N',         False) or pressed.get('n',         False)


class Level:
    def __init__(self):
        def makeIsland(w, h):
            x = randint(border, LEVEL_WIDTH_TILES - border - w - 1)
            z = randint(border, LEVEL_HEIGHT_TILES - border - h - 1)
            return RectXZ(x, z, x + w, z + h)

        def fillrect(x1, z1, x2, z2, type):
            for tz in range(min(z1, z2), max(z1, z2) + 1):
                for tx in range(min(x1, x2), max(x1, x2) + 1):
                    self.tiles[tz * LEVEL_WIDTH_TILES + tx] = type

        self.tiles = array('B', [0 for n in range(LEVEL_WIDTH_TILES * LEVEL_HEIGHT_TILES)])
        border = 1

        # Big islands
        islands  = [makeIsland(randint(LEVEL_WIDTH_TILES  // 5, LEVEL_WIDTH_TILES  // 3),
                               randint(LEVEL_HEIGHT_TILES // 5, LEVEL_HEIGHT_TILES // 3))
                    for _ in range(randint(5, 10))]
        # Medium islands
        islands += [makeIsland(randint(LEVEL_WIDTH_TILES  // 10, LEVEL_WIDTH_TILES  // 5),
                               randint(LEVEL_HEIGHT_TILES // 10, LEVEL_HEIGHT_TILES // 5))
                    for _ in range(randint(1, 50))]

        startIsland = islands[randint(0, len(islands) - 1)]
        startTilex = randint(startIsland.x1 + 2, startIsland.x2 - 2)
        startTilez = randint(startIsland.z1 + 2, startIsland.z2 - 6)
        self.startx = startTilex * TILE_WIDTH
        self.startz = startTilez * TILE_HEIGHT

        # Goal shouldn't be too close to start position
        # Placing goal on an existing island could cause an infinite
        # loop, as there is no guarantee a suitable island is available
        goalTilex = startTilex
        goalTilez = startTilez
        while circleContainsPoint(goalTilex, goalTilez, LEVEL_WIDTH_TILES // 3, startTilex, startTilez):
            goalTilex = randint(3, LEVEL_WIDTH_TILES - 4)
            goalTilez = randint(3, LEVEL_HEIGHT_TILES - 8)

        # Small goal island
        goalIslandw = randint(LEVEL_WIDTH_TILES // 20, LEVEL_WIDTH_TILES // 10)
        goalIslandh = randint(LEVEL_WIDTH_TILES // 20, LEVEL_WIDTH_TILES // 10)
        goalIslandx = randint(max(border, goalTilex - goalIslandw + 2),
                              min(LEVEL_WIDTH_TILES - border - goalIslandw - 1, goalTilex - 2))
        goalIslandz = randint(max(border, goalTilez - goalIslandh + 6),
                              min(LEVEL_HEIGHT_TILES - border - goalIslandh - 1, goalTilez - 2))
        islands.append(RectXZ(goalIslandx, goalIslandz,
                              goalIslandx + goalIslandw, goalIslandz + goalIslandh))
        self.goal = Elevator(goalTilex * TILE_WIDTH, goalTilez * TILE_HEIGHT)

        # Create bridges to connect all islands
        for n, island in enumerate(islands):
            if n > 0 and not any([island.intersectsOrTouches(island2) for island2 in islands[0:n]]):
                x = randint(island.x1, island.x2)
                z = randint(island.z1, island.z2)
                connected = False
                while not connected:
                    nextx = randint(border, LEVEL_WIDTH_TILES - border)
                    nextz = randint(border, LEVEL_HEIGHT_TILES - border)
                    for island2 in islands[0:n]:
                        if island2.z1 <= nextz < island2.z2:
                            nextx = randint(island2.x1, island2.x2)
                            connected = True
                            break
                        if island2.x1 <= nextx < island2.x2:
                            nextz = randint(island2.z1, island2.z2)
                            connected = True
                            break
                    fillrect(x, z, nextx, z, TILE_TYPE_GRASS)
                    x = nextx
                    fillrect(x, z, x, nextz, TILE_TYPE_GRASS)
                    z = nextz

        for island in islands:
            fillrect(island.x1, island.z1, island.x2, island.z2, TILE_TYPE_GRASS)

        # Tiny islands
        for _ in range(randint(0, 100)):
            island = makeIsland(randint(3, 5), randint(3, 5))
            fillrect(island.x1, island.z1, island.x2, island.z2, TILE_TYPE_GRASS)

        # Scatter inhabitants
        self.entities = []
        for _ in range(randint(15, 30)):
            x = randint(0, LEVEL_WIDTH  - TILE_WIDTH)
            z = randint(0, LEVEL_HEIGHT - TILE_HEIGHT)
            tileType = self.tileByCoord(x, z)
            # Do not generate a new location if the location is invalid as
            # that would increase population density on levels with little
            # land coverage
            if tileType == TILE_TYPE_GRASS:
                self.entities.append(Enemy(x, z))

    def tileByIndex(self, tilex, tilez):
        return self.tiles[tilez * LEVEL_WIDTH_TILES + tilex]

    def tileByCoord(self, x, z):
        return self.tileByIndex(math.floor(x / TILE_WIDTH), math.floor(z / TILE_HEIGHT))

    def collide(self, entity):
        for s in self.entities:
            if s is not entity and \
               cylindersIntersect(entity.x, entity.y, entity.z, entity.radius, entity.height,
                                  s.x, s.y, s.z, s.radius, s.height):
                return s


class Entity:
    def __init__(self, x, z, color):
        self.x = x
        self.y = 0
        self.z = z
        self.width = TILE_WIDTH
        self.height = TILE_HEIGHT * 2
        self.radius = self.width // 2
        self.color = color
        self.remove = False
        self.health = 0
        self.invulnerable = True

    def damage(self, damage):
        self.health -= damage
        self.remove = not self.invulnerable and self.health <= 0

    def draw(self, canvas, scrollx, scrolly, level):
        canvas.create_rectangle(self.x - self.width / 2 - scrollx,
                                self.z - self.y - self.height - scrolly,
                                self.x + self.width / 2 - scrollx,
                                self.z - self.y - scrolly,
                                fill=self.color, width=0)

inputDirections = {( 0,  0): (    0,     0, 1/4 * math.tau),
                   ( 1,  0): (    1,     0,              0),
                   ( 1,  1): ( .707,  .707, 1/8 * math.tau),
                   ( 0,  1): (    0,     1, 2/8 * math.tau),
                   (-1,  1): (-.707,  .707, 3/8 * math.tau),
                   (-1,  0): (   -1,     0, 4/8 * math.tau),
                   (-1, -1): (-.707, -.707, 5/8 * math.tau),
                   ( 0, -1): (    0,    -1, 6/8 * math.tau),
                   ( 1, -1): ( .707, -.707, 7/8 * math.tau)}

class Player(Entity):
    def __init__(self, x, z):
        super().__init__(x, z, 'red')
        self.vy = 0
        self.lastDirection = 1/4 * math.tau

    def handleInput(self, level, input):
        if self.y != 0:
            self.vy += GRAVITY
            if self.y > 0 and self.y + self.vy <= 0:
                self.vy = 0
            self.y += self.vy
            return
        if level.tileByCoord(self.x, self.z) == TILE_TYPE_SPACE:
            self.y = -1
            return

        if input.left or input.right or input.up or input.down:
            (dx, dz, self.lastDirection) = inputDirections[(input.right - input.left, input.down - input.up)]
            WALKING_SPEED = 3
            dx *= WALKING_SPEED
            dz *= WALKING_SPEED
            self.x = max(0, min(LEVEL_WIDTH,  self.x + dx))
            self.z = max(0, min(LEVEL_HEIGHT, self.z + dz))

        if input.action:
            level.entities.append(Projectile(self.x, self.z, self.lastDirection))

class Projectile(Entity):
    def __init__(self, x, z, direction):
        super().__init__(x, z, 'red')
        self.y = 24
        self.width  = TILE_WIDTH / 2
        self.height = TILE_WIDTH / 2
        THROW_SPEED = 6
        self.vx = THROW_SPEED * math.cos(direction)
        self.vz = THROW_SPEED * math.sin(direction)
        self.vy = 1

    def update(self, level):
        oldy = self.y
        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy
        self.z += self.vz

        if oldy > 0:
            # BUG: Projectiles shouldn't collide with each other
            s = level.collide(self)
            if s is not None:
                self.remove = True
                s.damage(1)
            elif self.y <= 0 and level.tileByCoord(self.x, self.z) != TILE_TYPE_SPACE:
                # Hit ground
                self.remove = True
        elif self.y < 0 and self.y - self.z <= level.player.y - level.player.z - VIEWPORT_HEIGHT / 2:
            # Fell deep into space
            self.remove = True

class Elevator(Entity):
    def __init__(self, x, z):
        super().__init__(x, z, 'orange')

class Enemy(Entity):
    def __init__(self, x, z):
        super().__init__(x, z, 'magenta')
        self.vx = 0
        self.vz = 0
        self.health = 2
        self.invulnerable = False

    def update(self, level):
        def decide():
            if random() > .4:
                direction = random() * math.tau
                SPEED = 2
                self.vx = SPEED * math.cos(direction)
                self.vz = SPEED * math.sin(direction)
            else:
                self.vx = 0
                self.vz = 0

        if random() > .99:
            decide()
        newx = self.x + self.vx
        newz = self.z + self.vz
        tileType = level.tileByCoord(newx, newz)
        if tileType != TILE_TYPE_GRASS:
            decide()
        else:
            self.x = newx
            self.z = newz


class Game:
    def __init__(self):
        self.showMap = False
        self.paused = False
        self.dirty = True
        self.initLevel()

    def initLevel(self):
        self.level = Level()
        self.player = Player(self.level.startx, self.level.startz)
        self.level.player = self.player

    def active(self):
        return not self.showMap

    def update(self, input):
        if input.pause:
            self.paused = not self.paused
        if self.paused:
            return
        if input.map:
            self.showMap = not self.showMap
            self.dirty = True
        if input.newMap:
            self.initLevel()
            self.dirty = True
        if self.showMap:
            return
        self.dirty = True
        self.player.handleInput(self.level, input)
        for s in self.level.entities:
            s.update(self.level)
        entityMax = len(self.level.entities) - 1
        for n, s in enumerate(reversed(self.level.entities)):
            if s.remove:
                del self.level.entities[entityMax - n]

    def draw(self, canvas):
        self.dirty = False
        if self.showMap:
            for tilez in range(0, LEVEL_HEIGHT_TILES):
                for tilex in range(0, LEVEL_WIDTH_TILES):
                    type = self.level.tileByIndex(tilex, tilez)
                    if type:
                        canvas.create_rectangle(tilex * VIEWPORT_WIDTH // (LEVEL_WIDTH_TILES - 1),
                                                tilez * VIEWPORT_HEIGHT // (LEVEL_HEIGHT_TILES - 1),
                                                (tilex + 1) * VIEWPORT_WIDTH // (LEVEL_WIDTH_TILES - 1),
                                                (tilez + 1) * VIEWPORT_HEIGHT // (LEVEL_HEIGHT_TILES - 1),
                                                fill=tileColors[type], width=0)
            # debug
            for s in self.level.entities:
                canvas.create_rectangle(s.x * VIEWPORT_WIDTH  // LEVEL_WIDTH  - TILE_WIDTH  // 2,
                                        s.z * VIEWPORT_HEIGHT // LEVEL_HEIGHT - TILE_HEIGHT // 2,
                                        s.x * VIEWPORT_WIDTH  // LEVEL_WIDTH  + TILE_WIDTH  // 2,
                                        s.z * VIEWPORT_HEIGHT // LEVEL_HEIGHT + TILE_HEIGHT // 2,
                                        fill=s.color, width=0)
            canvas.create_rectangle(self.level.goal.x * VIEWPORT_WIDTH  // LEVEL_WIDTH  - TILE_WIDTH  // 2,
                                    self.level.goal.z * VIEWPORT_HEIGHT // LEVEL_HEIGHT - TILE_HEIGHT // 2,
                                    self.level.goal.x * VIEWPORT_WIDTH  // LEVEL_WIDTH  + TILE_WIDTH  // 2,
                                    self.level.goal.z * VIEWPORT_HEIGHT // LEVEL_HEIGHT + TILE_HEIGHT // 2,
                                    fill=self.level.goal.color, width=0)
            canvas.create_rectangle(self.player.x * VIEWPORT_WIDTH  // LEVEL_WIDTH  - TILE_WIDTH  // 2,
                                    self.player.z * VIEWPORT_HEIGHT // LEVEL_HEIGHT - TILE_HEIGHT // 2,
                                    self.player.x * VIEWPORT_WIDTH  // LEVEL_WIDTH  + TILE_WIDTH  // 2,
                                    self.player.z * VIEWPORT_HEIGHT // LEVEL_HEIGHT + TILE_HEIGHT // 2,
                                    fill=self.player.color, width=0)
        else:
            if LEVEL_WIDTH <= VIEWPORT_WIDTH:
                scrollx = (LEVEL_WIDTH - VIEWPORT_WIDTH) // 2
            else:
                scrollx = max(0, min(LEVEL_WIDTH - VIEWPORT_WIDTH, math.floor(self.player.x) - VIEWPORT_WIDTH // 2))
            if LEVEL_HEIGHT <= VIEWPORT_HEIGHT:
                scrolly = (LEVEL_HEIGHT - VIEWPORT_HEIGHT) // 2
            else:
                scrolly = max(0, min(LEVEL_HEIGHT - VIEWPORT_HEIGHT, math.floor(self.player.z) - VIEWPORT_HEIGHT // 2))

            tilexStart = max(0, min(LEVEL_WIDTH_TILES,  scrollx // TILE_WIDTH))
            tilexStop  = max(0, min(LEVEL_WIDTH_TILES,  (scrollx + VIEWPORT_WIDTH) // TILE_WIDTH + 1))
            tilezStart = max(0, min(LEVEL_HEIGHT_TILES, scrolly // TILE_HEIGHT))
            tilezStop  = max(0, min(LEVEL_HEIGHT_TILES, (scrolly + VIEWPORT_HEIGHT) // TILE_HEIGHT + 1))

            entities = []
            entities += self.level.entities
            entities.append(self.level.goal)
            entities.append(self.player)
            entities.sort(key=lambda s:s.z)
            entityPos = 0

            for tilez in range(tilezStart, tilezStop):
                y = tilez * TILE_HEIGHT - scrolly
                while entityPos < len(entities):
                    s = entities[entityPos]
                    if s.z > y + scrolly: break
                    s.draw(canvas, scrollx, scrolly, self.level)
                    entityPos += 1
                for tilex in range(tilexStart, tilexStop):
                    type = self.level.tileByIndex(tilex, tilez)
                    if type:
                        color = tileColors[type]
                        if type == TILE_TYPE_GRASS and (tilex + tilez) & 1:
                            color = '#008800'
                        x = tilex * TILE_WIDTH  - scrollx
                        canvas.create_rectangle(x, y, x + TILE_WIDTH, y + TILE_HEIGHT, fill=color, width=0)
            while entityPos < len(entities):
                s = entities[entityPos]
                s.draw(canvas, scrollx, scrolly, self.level)
                entityPos += 1


def main():
    root = tkinter.Tk()
    canvas = tkinter.Canvas(root, width=VIEWPORT_WIDTH, height=VIEWPORT_HEIGHT, bg="black")
    canvas.pack()
    game = Game()
    input = Input()

    def update():
        input.update(keysHeld, keysPressed)
        keysPressed.clear()
        game.update(input)
        if game.dirty:
            canvas.delete("all")
            game.draw(canvas)
        if game.active():
            root.after(16, update)

    keysHeld = {}
    keysPressed = {}
    def keyPressed(event):
        keysHeld[event.keysym] = True
        keysPressed[event.keysym] = True
        if not game.active():
            update()

    def keyReleased(event):
        keysHeld[event.keysym] = False

    root.bind("<KeyPress>", keyPressed)
    root.bind("<KeyRelease>", keyReleased)
    update()
    root.mainloop()

if __name__ == "__main__":
    main()
