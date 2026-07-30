from bpy.props import PointerProperty
import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    FloatProperty,
    FloatVectorProperty,
    EnumProperty,
    StringProperty
    ,IntProperty
)

class AP_PaintSettings(PropertyGroup):

   
    layer_name: StringProperty(# type: ignore
        name="Layer Name",
        default="Layer"
    )
    brush_count: IntProperty(# type: ignore
        name="Brush Count",
        default=30,
        min=5,
        max=10000
    )
    brush_color: FloatVectorProperty(# type: ignore
        name="Color",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 1.0, 0.0, 1.0)
    )

    brush_size: FloatProperty(# type: ignore
        name="Size",
        min=0.001,
        max=100.0,
        default=10
    )

    brush_opacity: FloatProperty(# type: ignore
        name="Opacity",
        min=0.0,
        max=1.0,
        default=1.0
    )

    brush_strength: FloatProperty(# type: ignore
        name="Strength",
        min=0.0,
        max=1.0,
        default=1.0
    )
    brush_falloff: FloatProperty(# type: ignore
        name="Falloff",
        min=0.0,
        max=1.0,
        default=0.0
    )

    brush_image : PointerProperty(# type: ignore
        type=bpy.types.Image
    )
    # brush_falloff: EnumProperty(# type: ignore
    #     name="Falloff",
    #     items=[
    #         ('CONSTANT', 'Constant', ''),
    #         ('LINEAR', 'Linear', ''),
    #         ('SMOOTH', 'Smooth', ''),
    #         ('SPHERE', 'Sphere', ''),
    #     ],
    #     default='SMOOTH'
    # )