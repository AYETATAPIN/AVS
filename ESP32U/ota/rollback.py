from esp32 import Partition


def cancel() -> None:
    Partition.mark_app_valid_cancel_rollback()


def force() -> None:
    running = Partition(Partition.RUNNING)
    previous = running.get_next_update()
    previous.set_boot()


def info() -> dict:
    running = Partition(Partition.RUNNING)
    boot = Partition(Partition.BOOT)
    next_update = running.get_next_update()
    return {
        "running": running.info(),
        "boot": boot.info(),
        "next_update": next_update.info(),
    }
