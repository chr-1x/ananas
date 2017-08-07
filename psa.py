

class psa(Proboscidean):
    def init(self):
        pass
    def start(self):
        pass
    def stop(self):
        pass

    @scheduled(hour=0, day_of_week=0)
    @scheduled(hour=14, day_of_week=0)
    def announce_regs_opening(self):
        print("REGISTRATIONS ON CYBRESPACE OPENING SOON BABY!!")
        pass

    @scheduled(minute=0)
    def open_regs(self, time):
        print("OPENING REGISTRATIONS ON CYBRESPACE BABY!!")
        pass

    @scheduled(minute=0)
    def close_regs(self, time):
        hour = time[1]
        print("REGISTRATIONS ON CYBRESPACE CLOSING NOW BABY!!")
