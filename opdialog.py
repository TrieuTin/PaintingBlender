import bpy
class MsgDialog_OT_Get_Name(bpy.types.Operator):
    """Message Dialog"""
    bl_idname = "wm.message_dialog"
    bl_label = "Message Dialog"

    message = bpy.props.StringProperty(name="Message")

    def invoke(self,context,event):
        return context.window_manager.invoke_props_dialog(self  )
        
    def execute(self, context):
        context.scene.new_name=self.message        
        return {'FINISHED'}
classes = (MsgDialog_OT_Get_Name)

def register():
    """Register operators"""
    for cls in classes:
        bpy.utils.register_class(cls)
    

def unregister():
    """Unregister operators"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
