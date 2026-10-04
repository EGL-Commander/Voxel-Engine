# =============================================================================
# SAVE MANAGER — Persists just enough to reconstruct the world a player left:
# the seed (everything procedural regenerates from that), every block edit
# (break/place) layered ON TOP of the procedural generation, player position
# and look direction, selected hotbar slot, and inventory counts.
#
# What's deliberately NOT saved: the actual terrain. Storing every block in
# every chunk would be enormous and pointless — the seed regenerates it
# identically every time, so only the DIFFERENCES from that (the edits) need
# to be remembered.
# =============================================================================

import json
import os

SAVE_PATH = 'save.json'


class SaveManager:
    # -------------------------------------------------------------------------
    @staticmethod
    def load():
        """Returns the saved game state as a dict, or None if there's no save
        file yet (a brand-new game)."""
        if not os.path.exists(SAVE_PATH):
            return None

        with open(SAVE_PATH, 'r') as f:
            raw = json.load(f)

        # JSON object keys are always strings, but chunk/block coordinates
        # are tuples of ints — convert "cx,cz" and "lx,ly,lz" back.
        edits = {}
        for chunk_key, local_edits in raw.get('edits', {}).items():
            cx, cz = (int(v) for v in chunk_key.split(','))
            edits[(cx, cz)] = {
                tuple(int(v) for v in local_key.split(',')): block_id
                for local_key, block_id in local_edits.items()
            }

        return {
            'seed':           raw['seed'],
            'player_x':       raw['player']['x'],
            'player_y':       raw['player']['y'],
            'player_z':       raw['player']['z'],
            'yaw':            raw['player']['yaw'],
            'pitch':          raw['player']['pitch'],
            'selected_block': raw['selected_block'],
            # JSON object keys are strings even for an int-keyed dict, so
            # inventory counts need their keys converted back to ints too.
            'inventory':      {int(k): v for k, v in raw['inventory'].items()},
            'edits':          edits,
        }

    # -------------------------------------------------------------------------
    @staticmethod
    def save(seed, player_position, yaw, pitch, selected_block, inventory, edits):
        edits_out = {
            f"{cx},{cz}": {
                f"{lx},{ly},{lz}": block_id
                for (lx, ly, lz), block_id in local_edits.items()
            }
            for (cx, cz), local_edits in edits.items()
        }

        data = {
            'seed': seed,
            'player': {
                'x': player_position.x, 'y': player_position.y, 'z': player_position.z,
                'yaw': yaw, 'pitch': pitch,
            },
            'selected_block': selected_block,
            'inventory':      inventory,
            'edits':          edits_out,
        }

        # Write to a temp file and rename over the real one — if the game
        # crashes or is killed mid-write, you're left with either the old
        # save or the new one, never a half-written corrupt file.
        tmp_path = SAVE_PATH + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(data, f)
        os.replace(tmp_path, SAVE_PATH)
