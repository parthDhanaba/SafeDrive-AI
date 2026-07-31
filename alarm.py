import pygame


class AlarmManager:

    def __init__(self):

        pygame.mixer.init()

        self.sound = pygame.mixer.Sound("assets/alarm.mp3")

        self.playing = False

    def play(self):

        if not self.playing:
            self.sound.play(-1)
            self.playing = True

    def stop(self):

        if self.playing:
            self.sound.stop()
            self.playing = False