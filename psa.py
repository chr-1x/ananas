from pineapple import PineappleBot, schedule, interval
import time

class psa(PineappleBot):
    def init(self):
        pass
    def start(self):
        pass
    def stop(self):
        pass

    #@scheduled(hour=0, day_of_week=0)
    #@scheduled(hour=14, day_of_week=0)
    #def announce_regs_opening(self):
    #    print("REGISTRATIONS ON CYBRESPACE OPENING SOON BABY!!")
    #    pass

    @schedule(hour=14, minute=9)
    @schedule(month=8, hour=13, minute=8)
    @schedule(day_of_month=12, hour=13, minute=7)
    def open_regs(self):
        print("OPENING REGISTRATIONS ON CYBRESPACE BABY!!")
        pass

    @interval(3600)
    def close_regs(self):
        print("REGISTRATIONS ON CYBRESPACE CLOSING NOW BABY!!")
