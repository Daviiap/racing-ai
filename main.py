import pygame
import time
import math
import neat
import os

from utils import scale_image, blit_rotate_center, blit_text_center, contains
pygame.font.init()

generation = 0
GRASS = scale_image(pygame.image.load("imgs/grass.jpg"), 2.5)
TRACK = scale_image(pygame.image.load("imgs/track.png"), 0.9)

TRACK_BORDER = scale_image(pygame.image.load("imgs/track-border.png"), 0.9)
TRACK_BORDER_MASK = pygame.mask.from_surface(TRACK_BORDER)

FINISH = pygame.image.load("imgs/finish.png")
FINISH_MASK = pygame.mask.from_surface(FINISH)
FINISH_POSITION = (130, 250)

RED_CAR = scale_image(pygame.image.load("imgs/red-car.png"), 0.40)
GREEN_CAR = scale_image(pygame.image.load("imgs/green-car.png"), 0.40)

CAR_WIDTH, CAR_HEIGHT = RED_CAR.get_width(), RED_CAR.get_height()

WIDTH, HEIGHT = TRACK.get_width(), TRACK.get_height()
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Racing Game!")

MAIN_FONT = pygame.font.SysFont("comicsans", 44)

FPS = 60
PATH = [(175, 119), (110, 70), (56, 133), (70, 481), (318, 731), (404, 680), (418, 521), (507, 475), (600, 551), (613, 715), (736, 713),
        (734, 399), (611, 357), (409, 343), (433, 257), (697, 258), (738, 123), (581, 71), (303, 78), (275, 377), (176, 388), (178, 260)]


class GameInfo:
    LEVELS = 10

    def __init__(self):
        self.started = False

    def reset(self):
       self.started = False

    def game_finished(self):
        return self.level > self.LEVELS

    def start(self):
        self.started = True

class AbstractCar:
    def __init__(self, max_vel, rotation_vel):
        self.img = self.IMG
        self.max_vel = max_vel
        self.vel = 0
        self.rotation_vel = rotation_vel
        self.angle = 0
        self.x, self.y = self.START_POS
        self.acceleration = 0.1

    def rotate(self, left=False, right=False):
        if left:
            self.angle += self.rotation_vel
        elif right:
            self.angle -= self.rotation_vel

    def draw(self, win):
        blit_rotate_center(win, self.img, (self.x, self.y), self.angle)

    def move_forward(self):
        self.vel = min(self.vel + self.acceleration, self.max_vel)
        self.move()

    def move_backward(self):
        self.vel = max(self.vel - self.acceleration, -self.max_vel/2)
        self.move()

    def move(self):
        radians = math.radians(self.angle)
        vertical = math.cos(radians) * self.vel
        horizontal = math.sin(radians) * self.vel

        self.y -= vertical
        self.x -= horizontal

    def collide(self, mask, x=0, y=0):
        car_mask = pygame.mask.from_surface(self.img)
        offset = (int(self.x - x), int(self.y - y))
        poi = mask.overlap(car_mask, offset)
        return poi

    def reset(self):
        self.x, self.y = self.START_POS
        self.angle = 0
        self.vel = 0


class SensorBullet:
    def __init__(self, car, base_angle, vel, color):
        self.x = car.x + CAR_WIDTH/2
        self.y = car.y + CAR_HEIGHT/2
        self.angle = car.angle
        self.base_angle = base_angle
        self.vel = vel
        self.color = color
        self.img = pygame.Surface((4, 4))
        self.fired = False
        self.hit = False
        self.last_poi = None

    def draw(self, win):
        pygame.draw.circle(win, self.color, (self.x, self.y), 2)

    def fire(self, car):
        self.angle = car.angle + self.base_angle
        self.x = car.x + CAR_WIDTH/2
        self.y = car.y + CAR_HEIGHT/2
        self.fired = True
        self.hit = False

    def move(self):
        if(self.fired):
            radians = math.radians(self.angle)
            vertical = math.cos(radians) * self.vel
            horizontal = math.sin(radians) * self.vel

            self.y -= vertical
            self.x -= horizontal

    def collide(self, x=0, y=0):
        bullet_mask = pygame.mask.from_surface(self.img)
        offset = (int(self.x - x), int(self.y - y))
        poi = TRACK_BORDER_MASK.overlap(bullet_mask, offset)
        if poi:
            self.fired = False
            self.hit = True
            self.last_poi = poi
        return poi

    def draw_line(self, win, car):
        if self.hit:
            pygame.draw.line(win, self.color, (car.x + CAR_WIDTH/2, car.y + CAR_HEIGHT/2), (self.x, self.y), 1)
            pygame.display.update()

    def get_distance_from_poi(self, car):
        if self.last_poi is None:
            return -1
        return math.sqrt((car.x - self.last_poi[0])**2 + (car.y - self.last_poi[1])**2)


class PlayerCar(AbstractCar):
    IMG = RED_CAR
    START_POS = (180, 200)

    def __init__(self, max_vel, rotation_vel):
        super().__init__(max_vel, rotation_vel)
        self.sensors = [
            SensorBullet(self, 170, 20, (0, 0, 255)),
            SensorBullet(self, 135, 20, (0, 0, 255)),
            SensorBullet(self, 90, 12, (0, 0, 255)),
            SensorBullet(self, 45, 12, (0, 0, 255)),
            SensorBullet(self, 10, 12, (0, 0, 255)),
            SensorBullet(self, -10, 12, (0, 0, 255)),
            SensorBullet(self, -45, 12, (0, 0, 255)),
            SensorBullet(self, -90, 12, (0, 0, 255)),
            SensorBullet(self, -135, 20, (0, 0, 255)),
            SensorBullet(self, -170, 20, (0, 0, 255)),
            ]

    def reduce_speed(self):
        self.vel = max(self.vel - self.acceleration / 2, 0)
        self.move()

    def bounce(self):
        self.vel = -self.vel
        self.move()

    def fireSensors(self): 
        for bullet in self.sensors:
            bullet.fire(self)
    
    def sensorControl(self):
        for bullet in self.sensors:
            if not bullet.fired:
                bullet.fire(self)

        for bullet in self.sensors:
            bullet.move()
    
    def get_distance_array(self):
        return [bullet.get_distance_from_poi(self) for bullet in self.sensors]


class ComputerCar(AbstractCar):
    IMG = GREEN_CAR
    START_POS = (150, 200)

    def __init__(self, max_vel, rotation_vel, path=[]):
        super().__init__(max_vel, rotation_vel)
        self.path = path
        self.current_point = 0
        self.vel = max_vel

    def draw_points(self, win):
        for point in self.path:
            pygame.draw.circle(win, (255, 0, 0), point, 5)

    def draw(self, win):
        super().draw(win)

    def calculate_angle(self):
        target_x, target_y = self.path[self.current_point]
        x_diff = target_x - self.x
        y_diff = target_y - self.y

        if y_diff == 0:
            desired_radian_angle = math.pi / 2
        else:
            desired_radian_angle = math.atan(x_diff / y_diff)

        if target_y > self.y:
            desired_radian_angle += math.pi

        difference_in_angle = self.angle - math.degrees(desired_radian_angle)
        if difference_in_angle >= 180:
            difference_in_angle -= 360

        if difference_in_angle > 0:
            self.angle -= min(self.rotation_vel, abs(difference_in_angle))
        else:
            self.angle += min(self.rotation_vel, abs(difference_in_angle))

    def update_path_point(self):
        target = self.path[self.current_point]
        rect = pygame.Rect(
            self.x, self.y, self.img.get_width(), self.img.get_height())
        if rect.collidepoint(*target):
            self.current_point += 1

    def move(self):
        if self.current_point >= len(self.path):
            return

        self.calculate_angle()
        self.update_path_point()
        super().move()


def draw(win, images, cars):
    
    for img, pos in images:
        win.blit(img, pos)

    for img, pos in images:
        win.blit(img, pos)

    for car in cars:
        car.draw(win)
        for bullet in car.sensors:
            bullet.draw(win)

    pygame.display.update()


def move_player(player_car, outputs):
    if outputs[0] > 0.5:
        player_car.rotate(left=True)
    
    if outputs[1] > 0.5:
        player_car.rotate(right=True)

    player_car.move_forward()
    
def handle_collision(player_car):

    for bullet in player_car.sensors:
        if bullet.collide() != None:
            bullet.draw_line(WIN, player_car)

    if player_car.collide(TRACK_BORDER_MASK) != None:
        return True
    
def main(genomes, config):
    global generation
    generation += 1

    clock = pygame.time.Clock()
    images = [(GRASS, (0, 0)), (TRACK, (0, 0)),
            (FINISH, FINISH_POSITION), (TRACK_BORDER, (0, 0))]
    
    nets = []
    cars = []
    ge_list = []

    for _, genome in genomes:
        net = neat.nn.FeedForwardNetwork.create(genome, config)
        nets.append(net)

        genome.fitness = 0
        ge_list.append(genome)

        cars.append(PlayerCar(8, 5))

    run = True
    while len(cars) > 0 and run:
        clock.tick(FPS)

        draw(WIN, images, cars)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

        for i, car in enumerate(cars):         
            inputs = car.get_distance_array()
            inputs.append(car.vel)

            output = nets[i].activate(inputs)

            old_x, old_y = car.x, car.y
            move_player(car, output)

            isCollide = handle_collision(car)

            if isCollide:
                ge_list[i].fitness -= 1
                cars.pop(i)
                nets.pop(i)
                ge_list.pop(i)
            else:
                if old_x == car.x and old_y == car.y:
                    ge_list[i].fitness -= 1
                    cars.pop(i)
                    nets.pop(i)
                    ge_list.pop(i)
                else:
                    if car.vel < 0:
                        ge_list[i].fitness -= 1
                        cars.pop(i)
                        nets.pop(i)
                        ge_list.pop(i)
                    else:
                        ge_list[i].fitness += car.vel/10

def run(path_config):
	config = neat.config.Config(neat.DefaultGenome,
								neat.DefaultReproduction,
								neat.DefaultSpeciesSet,
								neat.DefaultStagnation,
								path_config)

	population = neat.Population(config)
	population.add_reporter(neat.StdOutReporter(True))
	population.add_reporter(neat.StatisticsReporter())
	population.run(main, 50)

if __name__ == '__main__': 
	path = os.path.dirname(__file__)
	path_config = os.path.join(path, 'config.txt')
	run(path_config)
