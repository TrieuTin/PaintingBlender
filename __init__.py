# __init__.py

bl_info = {
   "name": "AutoPaint Layer & Path System",
    "author": "Tin",
    "version": (4, 5),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Hatde",
    "description": "Layer Paint & 3D Path Ribbon System for Blender 4.x",
    "category": "Paint",
}


from CodePY import operators
from CodePY import panels

def register():
    """Register addon"""
    print("=" * 50)
    print("Registering AutoPaint Layer & Path System...")
    
    operators.register()
    panels.register()
    
    print("=" * 50)
    print("Addon loaded successfully!")
    print("=" * 50)

def unregister():
    """Unregister addon"""
    print("=" * 50)
    print("Unregistering AutoPaint Layer & Path System...")
    
    panels.unregister()
    operators.unregister()
    
    print("=" * 50)
    print("Addon unloaded!")
    print("=" * 50)

if __name__ == "__main__":
    register()