bl_info = {
    "name": "Action Organizer",
    "description": "",
    "author": "Samjooma",
    "version": (1, 0, 0),
    "blender": (4, 1, 0),
    "category": "Animation"
}

import bpy
from . import action_organizer_operator

def register():
    action_organizer_operator.register()

def unregister():
    action_organizer_operator.unregister()

if __name__ == "__main__":
    register()