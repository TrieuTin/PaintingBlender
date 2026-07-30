# panels.py

import bpy
from bpy.types import Panel
from . import PropertiesUI
from .Proceduce import PREFIX
from .utilities import MY_OT_ReloadAddon  # Import operator reload
#from .operators import AUTOPAINT_OT_generate_path, AUTOPAINT_OT_start_curve_draw, AUTOPAINT_OT_init_core, AUTOPAINT_OT_delete_layer, AUTOPAINT_OT_add_layer, AUTOPAINT_OT_toggle_layer

class PT_ReloadPanel(Panel):
    """Reload Panel"""
    bl_label = "Update Code"
    bl_idname = "PT_ReloadPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hat_De1"
  
    def draw(self, context):
        layout = self.layout
        
        row = layout.row()
        row.label (text="Update Code after change file code")
        row = layout.row()
        row.operator("wm.reload_addon", text="Update Addon", icon='FILE_REFRESH')

class PT_MainPanel(Panel):
    """Panel UI chính"""
    bl_label = "Create Spline"
    bl_idname = "PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hat_De1"
    
    def draw(self, context):
        layout = self.layout
        
        obj = context.active_object
        
        if not obj:
            layout.label(text="No Object Selected")
           # layout.separator()
           # layout.operator("wm.reload_addon", text="Reload Addon", icon='FILE_REFRESH')
           
            return
        # Header
       
        # --- BOX 1: LAYER MANAGER SYSTEM ---
        #box_layer = layout.box()
        #box_layer.label(text="Layers", icon='NODETREE')
        #box_layer.operator("autopaint.init_core", icon='NODE_MATERIAL')
        #box_layer.operator("autopaint.add_layer", icon='BRUSH_DATA')
       

        if obj.data and obj.data.materials and obj.data.materials[0].use_nodes:
            nodes = obj.data.materials[0].node_tree.nodes
            group_nodes = sorted(
                [n for n in nodes if n.type == 'GROUP' and n.label.startswith(PREFIX)],
                key=lambda x: x.location.y,reverse=True)
            for n in group_nodes:
                row_box = layout.box()
                row = row_box.row(align=True)

                eye_icon = 'HIDE_OFF' if not n.mute else 'HIDE_ON'
                op_eye = row.operator("autopaint.toggle_layer", text="", icon=eye_icon)
                #op_eye.node_name = n.name

                row.label(text="Hide/Alpha")
                #Float opacity
                row.prop(n.inputs['Opacity'], "default_value", text="", slider=True)

                tex_name = ""
                for link in n.inputs['Paint Color'].links:
                    tex_name = link.from_node.name

                # op_del = row.operator("autopaint.delete_layer", text="", icon='TRASH')
                # op_del.node_name = n.name
                # op_del.tex_name = tex_name
        box_path = layout.box()
        box_path.label(text="3D Path Paint Tools (Substance)", icon='CURVE_DATA')
        
        # Nút bước 1: Bật chế độ cọ vẽ bám dính bề mặt
        box_path.operator("autopaint.start_curve_draw", text="1. Initialize Path", icon='LINE_DATA')
        
        # Nút bước 2: Bấm xác nhận sinh mạng lưới Ribbon phẳng ôm sát
       
        box_path.operator("autopaint.generate_path",text="2. Generate Path",icon='GEOMETRY_NODES')
        box_path.label(text="Start")
        geo_mod = next((m for m in obj.modifiers if m.type == 'NODES'),None)

        if geo_mod and geo_mod.node_group:

            geo_nodes = geo_mod.node_group.nodes

            curve_line = next((n for n in geo_nodes if n.type == 'CURVE_PRIMITIVE_LINE'),None)
            resample_cur = next((n for n in geo_nodes if n.type == 'RESAMPLE_CURVE'),None)
            if curve_line:
                row = box_path.row()

                row.prop(curve_line.inputs["Start"],"default_value",index=0,text="X")
                row.prop(curve_line.inputs["Start"],"default_value",index=1,text="Y")
                row.prop(curve_line.inputs["Start"],"default_value",index=2,text="Z")

                row2 =box_path.row()
                row2.label(text="End")
                
                row3 = box_path.row()
                row3.prop(curve_line.inputs["End"],"default_value",index=0,text="X")
                row3.prop(curve_line.inputs["End"],"default_value",index=1,text="Y")
                row3.prop(curve_line.inputs["End"],"default_value",index=2,text="Z")
        
            if resample_cur:
                row4= box_path.row()
                row4.label(text="Smooth")
                row4.prop(resample_cur.inputs["Count"],"default_value")
        # Button gọi operator
        #layout.operator("wm.create_cube", text="Create Cube", icon='ADD')
        
        # Thêm button reload
        #layout.separator()
        #layout.operator("wm.reload_addon", text="Reload Addon", icon='FILE_REFRESH')

       
class Shader_PT_Diamond(bpy.types.Panel):
   
    bl_label = "Shader"
    bl_idname = "SHADER_PT_MAINPANEL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hat_De1"
    bl_parent_id = 'PT_MainPanel'
    def draw(self, context):
        layout = self.layout
        o = context.active_object
        row = layout.row()
        row.label(text= "Create Diamond")
        if o and o.type == "MESH":
            row.operator('shader.diamond_mat',text="Diamond Mat",icon='NODE_MATERIAL')



class AUTOPAINT_PT_paint_settings(bpy.types.Panel):

    bl_label = "Spline Paint"
    bl_idname = "AUTOPAINT_PT_paint_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Hat_De1'
   #bl_parent_id = 'PT_MainPanel'

    def draw(self, context):

        layout = self.layout
        settings = context.scene.settings

        box = layout.box()

        box.label(text="Brush Settings")
        box.prop(settings, "brush_color")
     
        box.prop(settings, "brush_count")
        box.prop(settings, "brush_size")
        box.prop(settings, "brush_opacity")
        box.prop(settings, "brush_strength")
        box.prop(settings, "brush_falloff")
        box.prop(settings, "brush_image")
        layout.separator()
        #add a material and layer 
        box = layout.box()

        box.label(
            text="Create Layer"
        )
        box.operator(
            "autopaint.add_layer",
            icon='PLUS'
        )

        # box.operator(
        #     "mesh.add_cube_button",
        #     icon='CUBE'
        # )
        box.operator(
            "mesh.add_cube_button",
            icon='CUBE'
        )

        # layout.operator(
        #     "autopaint.project_points",
        #     icon='MOD_SHRINKWRAP'
        # )
        # layout.operator("autopaint.debug_uv",
        # icon="UV")

        box = layout.box()

        box.label(
            text="Paint"
        )
       
        box.operator(
            "autopaint.paint_curve",
            icon='BRUSH_DATA'
        )





# Danh sách class UI cần register
classes = (PT_ReloadPanel,
PT_MainPanel, 
MY_OT_ReloadAddon,
AUTOPAINT_PT_paint_settings,
Shader_PT_Diamond,
) 


# Danh sách class UI cần register
classes = (PT_ReloadPanel,
PT_MainPanel, 
MY_OT_ReloadAddon,
AUTOPAINT_PT_paint_settings,
Shader_PT_Diamond,) 


def register():
    """Register panels"""
    bpy.utils.register_class(PropertiesUI.AP_PaintSettings)
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.settings = bpy.props.PointerProperty(
        type=PropertiesUI.AP_PaintSettings)
    print("Panels registered!")

def unregister():
    """Unregister panels"""
    del bpy.types.Scene.settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    bpy.utils.unregister_class(PropertiesUI.AP_PaintSettings)
    print("Panels unregistered!")