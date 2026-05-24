import time

class EmotionTimeline:
    def __init__(self, story_id):
        self.timelines = {
            1: [
                (0.0, 10.0, 'neutral'),
                (10.0, 22.0, 'sad'),
                (22.0, 36.0, 'angry'),
                (36.0, 43.0, 'excited'),
                (43.0, 55.0, 'love'),
                (55.0, 64.0, 'excited'),
                (64.0, 76.0, 'happy')
            ],
            2: [
                (0.0, 5.0, 'neutral'),
                (5.0, 9.0, 'excited'),
                (9.0, 13.0, 'sad'),
                (13.0, 25.0, 'excited'),
                (25.0, 30.0, 'sad'),
                (30.0, 37.0, 'neutral'),
                (37.0, 42.0, 'angry'),
                (42.0, 47.0, 'sad'),
                (47.0, 53.0, 'neutral'),
                (53.0, 58.0, 'happy'),
                (58.0, 64.0, 'love')
            ],
            3: [
                (0.0, 5.0, 'neutral'),
                (5.0, 12.0, 'sad'),
                (12.0, 17.0, 'angry'),
                (17.0, 25.0, 'neutral'),
                (25.0, 31.0, 'sad'),
                (31.0, 38.0, 'excited'),
                (38.0, 42.0, 'happy'),
                (42.0, 50.0, 'love'),
                (50.0, 53.0, 'happy'),
                (53.0, 62.0, 'love')
            ],
            4: [
                (0.0, 3.0, 'neutral'),
                (3.0, 9.0, 'love'),
                (9.0, 15.0, 'excited'),
                (15.0, 26.0, 'sad'),
                (26.0, 34.0, 'angry'),
                (34.0, 47.0, 'love'),
                (47.0, 56.0, 'happy'),
                (56.0, 67.0, 'love')
            ],
            5: [
                (0.0, 7.0, 'neutral'),
                (7.0, 10.0, 'happy'),
                (10.0, 16.0, 'sad'),
                (16.0, 28.0, 'angry'),
                (28.0, 33.0, 'sad'),
                (33.0, 39.0, 'love'),
                (39.0, 46.0, 'excited')
            ],
            6: [
                (0.0, 11.0, 'sad'),
                (11.0, 21.0, 'angry'),
                (21.0, 27.0, 'sad'),
                (27.0, 34.0, 'happy'),
                (34.0, 37.0, 'love'),
                (37.0, 40.0, 'sad'),
                (40.0, 45.0, 'love'),
                (45.0, 50.0, 'happy')
            ],
            7: [
                (0.0, 8.0, 'happy'),
                (8.0, 14.0, 'love'),
                (14.0, 21.0, 'angry'),
                (21.0, 33.0, 'sad'),
                (33.0, 40.0, 'love'),
                (40.0, 47.0, 'happy')
            ],
            8: [
                (0.0, 2.0, 'neutral'),
                (2.0, 10.0, 'happy'),
                (10.0, 13.0, 'excited'),
                (13.0, 20.0, 'sad'),
                (20.0, 26.0, 'angry'),
                (26.0, 30.0, 'neutral'),
                (30.0, 34.0, 'sad'),
                (34.0, 41.0, 'neutral'),
                (41.0, 48.0, 'love'),
                (48.0, 53.0, 'happy')
            ],
            9: [
                (0.0, 5.0, 'neutral'),
                (5.0, 10.0, 'excited'),
                (10.0, 15.0, 'sad'),
                (15.0, 18.0, 'happy'),
                (18.0, 25.0, 'angry'),
                (25.0, 28.0, 'sad'),
                (28.0, 34.0, 'love'),
                (34.0, 38.0, 'excited'),
                (38.0, 48.0, 'happy')
            ],
            10: [
                (0.0, 3.0, 'neutral'),
                (3.0, 8.0, 'love'),
                (8.0, 17.0, 'happy'),
                (17.0, 21.0, 'angry'),
                (21.0, 28.0, 'neutral'),
                (28.0, 35.0, 'sad'),
                (35.0, 42.0, 'love'),
                (42.0, 49.0, 'happy')
            ]
        }

        if story_id not in self.timelines:
            raise ValueError(f"Story ID {story_id} not found in timelines")

        self.current_emotion = None
        self.story_id = story_id
        self.start_time = None
        self.paused_time = None
        self.accumulated_paused = 0.0

    def start(self):
        self.start_time = time.time()
        self.paused_time = None
        self.accumulated_paused = 0.0

    def pause(self):
        if self.start_time and not self.paused_time:
            self.paused_time = time.time()

    def resume(self):
        if self.paused_time:
            self.accumulated_paused += time.time() - self.paused_time
            self.paused_time = None

    def get_current_emotion(self):
        if not self.start_time:
            return None

        if self.paused_time:
            elapsed = self.paused_time - self.start_time - self.accumulated_paused
        else:
            elapsed = time.time() - self.start_time - self.accumulated_paused

        for start, end, emotion in self.timelines[self.story_id]:
            if start <= elapsed < end:
                if emotion != self.current_emotion:
                    self.current_emotion = emotion
                return emotion

        return None