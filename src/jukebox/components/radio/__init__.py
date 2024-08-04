import logging
import threading
import jukebox.cfghandler
import jukebox.plugs as plugin
from components.playermpd import player_ctrl
from gpiozero import MCP3008
import time

logger = logging.getLogger('jb.radio')
cfg = jukebox.cfghandler.get_handler('jukebox')


@plugin.register
def play_radio(folder: str, recursive: bool = False):
    # wenn noch einmal gedrückt dann stoppen bspw. durch globale variabel
    player_ctrl.play_folder(folder, recursive)
    player_ctrl.radio_event.clear()
    start = 0.2
    stop = 1

    plst_len = len(player_ctrl.playlistinfo())
    logger.info(f"Playlist length: '{plst_len}'")

    def radio(client):
        prev_songpos = None
        while not client.radio_event.is_set():
            songpos = int((MCP3008(2).value - start) / ((stop - start) / (plst_len - 1)))
            if songpos != prev_songpos:
                try:
                    client.seeks(songpos, 0)
                    logger.info(f"Songpos: '{songpos}'")
                    prev_songpos = songpos
                    logger.info(f"radio_event: '{client.radio_event.is_set()}'")
                except Exception as e:
                    logger.error(
                        f"{e.__class__.__qualname__}: {e} at songpos {songpos}")
            time.sleep(0.1)

    threading.Thread(target=radio, daemon=True, args=(player_ctrl,)).start()
