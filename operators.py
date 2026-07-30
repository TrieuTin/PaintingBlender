# operators.py

from bpy.ops import brush
from .CurveUtils import get_uv_from_hit, project_points_to_mesh
from bl_ui import properties_data_empty
import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from . import Proceduce
from .CurveUtils import sample_curve_points,  paint_brush_on_image, uv_to_pixel, paint_pixel, paint_circle_on_image
# paint_uv_line,
# Toggle layer 
# =========================================================
class AUTOPAINT_OT_toggle_layer(Operator):
    bl_idname = "autopaint.toggle_layer"
    bl_label = "Toggle Layer"
    node_name = StringProperty()

    def execute(self, context):
        obj = context.active_object
        mat = obj.data.materials[0]
        node = mat.node_tree.nodes.get(self.node_name)
        if node:
            node.mute = not node.mute
        return {'FINISHED'}

# ADD LAYER 
# =========================================================

class AUTOPAINT_OT_add_layer(bpy.types.Operator):
    bl_idname = "autopaint.add_layer"
    bl_label = "Add Layer"
    bl_options = {'REGISTER', 'UNDO'}

    layer_name= StringProperty(name="Layer Name", default="Layer")

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and context.active_object.type == 'MESH')

    def execute(self, context):
        obj = context.active_object
        mat = Proceduce.safe_get_material(obj)
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        principled = Proceduce.setup_initial_pbr_network(mat.node_tree)

        existing_groups = [n for n in nodes if n.type == 'GROUP' and n.label.startswith(Proceduce.PREFIX)]
        layer_index = len(existing_groups) + 1

        image = bpy.data.images.new(
            name=f"{Proceduce.PREFIX}IMG_{layer_index}",
            width=2048,
            height=2048,
            alpha=True
        )
        image.generated_color = (0.0, 0.0, 0.0, 0.0)

        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.image = image
        tex_node.location = (-900, -300 * layer_index)
        tex_node.label = f"Texture_{layer_index}"

        group_tree = Proceduce.create_layer_group(f"{Proceduce.PREFIX}GROUP_{layer_index}")

        group_node = nodes.new('ShaderNodeGroup')
        group_node.node_tree = group_tree
        group_node.label = f"{Proceduce.PREFIX}Layer_{layer_index}"
        group_node.location = (-500, -300 * layer_index)

        group_node.inputs['Opacity'].default_value = 1.0

        links.new(tex_node.outputs['Color'], group_node.inputs['Paint Color'])
        links.new(tex_node.outputs['Alpha'], group_node.inputs['Paint Alpha'])

        base_input = principled.inputs['Base Color']

        if not base_input.is_linked:
            group_node.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)
            links.new(group_node.outputs['Result'], base_input)
        else:
            old_link = base_input.links[0]
            old_source = old_link.from_socket
            links.remove(old_link)

            links.new(old_source, group_node.inputs['Base Color'])
            links.new(group_node.outputs['Result'], base_input)

        bpy.ops.object.mode_set(mode='TEXTURE_PAINT')
        for n in nodes:
            n.select = False

        tex_node.select = True
        nodes.active = tex_node

        return {'FINISHED'}

#Delete layer
# =========================================================
class AUTOPAINT_OT_delete_layer(bpy.types.Operator):
    bl_idname = "autopaint.delete_layer"
    bl_label = "Delete Layer"
    node_name= StringProperty()
    tex_name= StringProperty()

    def execute(self, context):
        obj = context.active_object
        mat = obj.data.materials[0]
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        g_node = nodes.get(self.node_name)
        t_node = nodes.get(self.tex_name)

        if not g_node:
            return {'CANCELLED'}

        input_socket = g_node.inputs['Base Color']
        output_socket = g_node.outputs['Result']

        source_socket = None
        destinations = []

        if input_socket.is_linked:
            source_socket = input_socket.inputs[0].links[0].from_socket

        if output_socket.is_linked:
            for link in output_socket.links:
                destinations.append(link.to_socket)

        for link in list(g_node.inputs['Base Color'].links):
            links.remove(link)
        for link in list(g_node.outputs['Result'].links):
            links.remove(link)

        if t_node:
            nodes.remove(t_node)
        nodes.remove(g_node)

        if source_socket:
            for dest in destinations:
                links.new(source_socket, dest)

        return {'FINISHED'}
    #========================================================

#Init core ================================================
class AUTOPAINT_OT_init_core(bpy.types.Operator):
    bl_idname = "autopaint.init_core"
    bl_label = "Initialize Core"

    def execute(self, context):
        obj = context.active_object
        mat = Proceduce.safe_get_material(obj)
        Proceduce.setup_initial_pbr_network(mat.node_tree)
        return {'FINISHED'}

#Draw Curve ==========================================================
class AUTOPAINT_OT_start_curve_draw(bpy.types.Operator):
    """Bắt đầu vẽ Curve bám lên Mesh"""
    
    bl_idname = "autopaint.start_curve_draw"
    bl_label = "Start Draw Path"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None and
            context.active_object.type == 'MESH'
        )

    def execute(self, context):

        mesh_obj = context.active_object

        # Chuyển về Object Mode
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # ------------------------------------------------
        # Tạo Curve
        # ------------------------------------------------

        curve_data = bpy.data.curves.new(
            name=f"{Proceduce.PREFIX}PathData",
            type='CURVE'
        )

        curve_data.dimensions = '3D'

        curve_obj = bpy.data.objects.new(name=f"{Proceduce.PREFIX}Path_Stroke",object_data=curve_data)

        context.collection.objects.link(curve_obj)

        # Lưu mesh target
        curve_obj["target_mesh"] = mesh_obj.name

        # ------------------------------------------------
        # Active Curve
        # ------------------------------------------------

        bpy.ops.object.select_all(action='DESELECT')

        curve_obj.select_set(True)

        context.view_layer.objects.active = curve_obj

        # ------------------------------------------------
        # Edit Mode
        # ------------------------------------------------

        bpy.ops.object.mode_set(mode='EDIT')

        # ------------------------------------------------
        # Chọn Draw Tool
        # ------------------------------------------------

        bpy.ops.wm.tool_set_by_id(name="builtin.draw")

        # ------------------------------------------------
        # Curve Paint Settings
        # ------------------------------------------------

        cps = context.scene.tool_settings.curve_paint_settings

        cps.curve_type = 'BEZIER'

        # SURFACE = bám mặt mesh
        cps.depth_mode = 'SURFACE'

        # Blender 4.x đôi khi không có attr này
        if hasattr(cps, "use_surface_project"):
            cps.use_surface_project = True

        self.report(
            {'INFO'},
            "Kéo chuột lên mesh để vẽ curve"
        )

        return {'FINISHED'}
#Generate Path========================================================
class AUTOPAINT_OT_generate_path(bpy.types.Operator):
    bl_idname = "autopaint.generate_path"
    bl_label = "Confirm & Generate Path"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'CURVE'

    def execute(self, context):
        curve_obj = context.active_object

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Clean old modifiers to prevent configuration conflicts
        old_geo = curve_obj.modifiers.get("AP_Ribbon")
        if old_geo:
            curve_obj.modifiers.remove(old_geo)

        old_shrink = curve_obj.modifiers.get("AP_Shrinkwrap")
        if old_shrink:
            curve_obj.modifiers.remove(old_shrink)

        # ---------------------------------------------------------------------
        # GENERATE GEOMETRY NODES SYSTEM
        # ---------------------------------------------------------------------
        geo_mod = curve_obj.modifiers.new(name="AP_Ribbon", type='NODES')
        node_tree = bpy.data.node_groups.new(name="AP_Ribbon_GeoTree", type='GeometryNodeTree')
        geo_mod.node_group = node_tree

        # Interface Socket Setup
        node_tree.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        node_tree.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

        nodes = node_tree.nodes
        links = node_tree.links

        # IO Blueprint Configuration
        group_input = nodes.new("NodeGroupInput")
        group_input.location = (-800, 200)
        group_output = nodes.new("NodeGroupOutput")
        group_output.location = (1200, 200)

        # Resample Curve Node
        resample = nodes.new("GeometryNodeResampleCurve")
        resample.location = (-600, 200)
        resample.inputs['Count'].default_value = 256  
        links.new(group_input.outputs[0], resample.inputs[0])

        # Set Curve Normal Initialization
        set_normal = nodes.new("GeometryNodeSetCurveNormal")
        set_normal.location = (-350, 200)
        links.new(resample.outputs[0], set_normal.inputs[0])

        # Profile Ribbon Construction (6mm total flattened width)
        profile_curve = nodes.new("GeometryNodeCurvePrimitiveLine")
        profile_curve.location = (-350, -100)
        profile_curve.inputs[0].default_value = (-0.003, 0, 0) 
        profile_curve.inputs[1].default_value = (0.003, 0, 0)  

        # Extrude curve path into actual mesh strip
        curve_to_mesh = nodes.new("GeometryNodeCurveToMesh")
        curve_to_mesh.location = (-50, 200)
        links.new(set_normal.outputs[0], curve_to_mesh.inputs[0])
        links.new(profile_curve.outputs[0], curve_to_mesh.inputs[1])

        # ---------------------------------------------------------------------
        # WARP UV COORDINATE GENERATION (STAGE 3)
        # ---------------------------------------------------------------------
        spline_param = nodes.new("GeometryNodeSplineParameter")
        spline_param.location = (-50, -100)

        combine_uv = nodes.new("ShaderNodeCombineXYZ")
        combine_uv.location = (200, -100)
        links.new(spline_param.outputs[1], combine_uv.inputs[1]) 

        store_uv = nodes.new("GeometryNodeStoreNamedAttribute")
        store_uv.location = (450, 200)
        store_uv.data_type = 'FLOAT_VECTOR'
        store_uv.domain = 'CORNER'
        store_uv.inputs[2].default_value = "UVMap" 
        links.new(curve_to_mesh.outputs[0], store_uv.inputs[0])
        links.new(combine_uv.outputs[0], store_uv.inputs[3])

        # Anti Z-Fighting Displacement (0.5mm surface elevation offset)
        set_position = nodes.new("GeometryNodeSetPosition")
        set_position.location = (700, 200)
        links.new(store_uv.outputs[0], set_position.inputs[0])

        normal_node = nodes.new("GeometryNodeInputNormal")
        normal_node.location = (450, -150)

        vector_scale = nodes.new("ShaderNodeVectorMath")
        vector_scale.operation = 'SCALE'
        vector_scale.location = (450, -300)
        vector_scale.inputs[3].default_value = 0.0005  
        links.new(normal_node.outputs[0], vector_scale.inputs[0])
        links.new(vector_scale.outputs[0], set_position.inputs[3])

        # ---------------------------------------------------------------------
        # DECAL MATERIAL AUTOGEN & INJECTION
        # ---------------------------------------------------------------------
        ribbon_mat = bpy.data.materials.get(f"{Proceduce.PREFIX}Ribbon_Decal_Material")
        if not ribbon_mat:
            ribbon_mat = bpy.data.materials.new(name=f"{Proceduce.PREFIX}Ribbon_Decal_Material")
            ribbon_mat.use_nodes = True
            
            mat_nodes = ribbon_mat.node_tree.nodes
            mat_links = ribbon_mat.node_tree.links
            bsdf = next((n for n in mat_nodes if n.type == 'BSDF_PRINCIPLED'), None)
            
            uv_attr = mat_nodes.new("ShaderNodeAttribute")
            uv_attr.attribute_name = "UVMap"
            uv_attr.location = (-600, 0)
            
            decal_tex = mat_nodes.new("ShaderNodeTexImage")
            decal_tex.name = f"{Proceduce.PREFIX}Decal_Texture_Node"
            decal_tex.location = (-350, 0)
            
            mat_links.new(uv_attr.outputs['Vector'], decal_tex.inputs['Vector'])
            if bsdf:
                mat_links.new(decal_tex.outputs['Color'], bsdf.inputs['Base Color'])
                mat_links.new(decal_tex.outputs['Alpha'], bsdf.inputs['Alpha'])

        set_material = nodes.new("GeometryNodeSetMaterial")
        set_material.location = (950, 200)
        set_material.inputs[2].default_value = ribbon_mat
        links.new(set_position.outputs[0], set_material.inputs[0])
        links.new(set_material.outputs[0], group_output.inputs[0])

        # FIX FOR EMPTY TAB: Force append the created material into Object's Physical Material Slots
        if not curve_obj.data.materials:
            curve_obj.data.materials.append(ribbon_mat)
        else:
            curve_obj.data.materials[0] = ribbon_mat

        # ---------------------------------------------------------------------
        # SHRINKWRAP ATTACHMENT
        # ---------------------------------------------------------------------
        target_name = curve_obj.get("target_mesh")
        if target_name:
            target_obj = bpy.data.objects.get(target_name)
            if target_obj:
                shrink = curve_obj.modifiers.new(name="AP_Shrinkwrap", type='SHRINKWRAP')
                shrink.target = target_obj
                shrink.wrap_method = 'NEAREST_SURFACEPOINT'
                shrink.wrap_mode = 'OUTSIDE'
                shrink.offset = 0.0005

        self.report({'INFO'}, "Warp UV Mapping & Decal Material configured cleanly!")
        return {'FINISHED'}
#Shader Diamond
#=====================================================================

class Shader_OT_Diamond(bpy.types.Operator):
    bl_label = "Diamond Shader"
    bl_idname = 'shader.diamond_mat'
    
    def execute(self,context):
        obj = context.active_object        
        #check obj is null
        if not obj and obj.type != 'Mesh':
            self.report({'ERROR'}, "Select a 3D object!")
            return {'CANCELLED'}
        
        # Ensure object has a material
        if not obj.data.materials:                    
            #Creating a new shader and naming 'diamond'
            mat_diamond = bpy.data.materials.new(name= "Diamond")
        else:
            mat_diamond = obj.data.materials[0]
        #Enable Use Nodes
        mat_diamond.use_nodes = True

        node = mat_diamond.node_tree.nodes
        #Removing Principled BSDF
        node.remove(node.get('Principled BSDF'))
        
        mat_Output = node.get('Material Output')
        
        mat_Output.location = (-400, 0)
        
        #Glass 1
        glass1_node = node.new('ShaderNodeBsdfGlass')    
            #Setting location
        glass1_node.location = (-600, 0)    
            #Change color to red
        glass1_node.inputs[0].default_value = (1, 0, 0, 1)        
            #Change IOR
        glass1_node.inputs[2].default_value = 1.446
        
          #Glass 2
        glass2_node = node.new('ShaderNodeBsdfGlass')    
            #Setting location
        glass2_node.location = (-600, -150)    
            #Change color to green
        glass2_node.inputs[0].default_value = (0, 1, 0, 1)        
            #Change IOR
        glass2_node.inputs[2].default_value = 1.450
        
          #Glass 3
        glass3_node = node.new('ShaderNodeBsdfGlass')    
            #Setting location
        glass3_node.location = (-600, -300)    
            #Change color to blue
        glass3_node.inputs[0].default_value = (0, 0, 1, 1)        
            #Change IOR
        glass3_node.inputs[2].default_value = 1.450
        
           #Glass 4
        glass4_node = node.new('ShaderNodeBsdfGlass')    
            #Setting location
        glass4_node.location = (-150, -150)    
            #Change color to white
        glass4_node.inputs[0].default_value = (1, 10, 1, 1)        
            #Change IOR
        glass4_node.inputs[2].default_value = 1.450
        glass4_node.select = False
        
        
          #Add Shader1
        AddShader1_node = node.new('ShaderNodeAddShader')    
            #Setting location
        AddShader1_node.location = (-400, -50)    
            #Change label
        AddShader1_node.label = "Add 1"
            #Minimize
        AddShader1_node.hide = True
        AddShader1_node.select = False

        #Add Shader2
        AddShader2_node = node.new('ShaderNodeAddShader')    
            #Setting location
        AddShader2_node.location = (-100, -50)    
            #Change label
        AddShader2_node.label = "Add 2"
            #Minimize
        AddShader2_node.hide = True
        AddShader2_node.select = False
        
        #Mix
        mix_node = node.new('ShaderNodeMixShader')
        mix_node.select = False
        mix_node.location = (200, 0)
        
        link = mat_diamond.node_tree.links
            #link glass1 to Add shader
        link.new(glass1_node.outputs[0], AddShader1_node.inputs[0])
        link.new(glass2_node.outputs[0], AddShader1_node.inputs[1])
        
        link.new(AddShader1_node.outputs[0], AddShader2_node.inputs[0])
        link.new(glass3_node.outputs[0], AddShader2_node.inputs[1])
        
        link.new(AddShader2_node.outputs[0], mix_node.inputs[1])
        link.new(glass4_node.outputs[0], mix_node.inputs[2])
        link.new(mix_node.outputs[0], mat_Output.inputs[0])
        
        bpy.context.object.active_material = mat_diamond
        
        return{'FINISHED'}
        

#save properties into spline
class AUTOPAINT_OT_apply_to_layer(bpy.types.Operator):
    bl_idname = "autopaint.apply_to_layer"
    bl_label = "Apply To Layer"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):

        obj = context.active_object

        return (
            obj is not None and
            obj.type == 'CURVE'
        )

    def execute(self, context):

        settings = context.scene.settings

        curve = context.active_object

        # ==========================
        # LAYER INFO
        # ==========================

        curve["ap_layer"] = settings.layer_name

        # ==========================
        # BRUSH INFO
        # ==========================

        curve["ap_color"] = list(settings.brush_color)

        curve["ap_size"] = settings.brush_size

        curve["ap_opacity"] = settings.brush_opacity

        curve["ap_strength"] = settings.brush_strength

        curve["ap_falloff"] = settings.brush_falloff

        # ==========================
        # STATUS
        # ==========================

        curve["ap_is_paint_curve"] = True

        # ==========================
        # TARGET MESH
        # ==========================

        target_mesh = curve.get("target_mesh")

        if target_mesh:
            curve["ap_target_mesh"] = target_mesh

        self.report(
            {'INFO'},
            f"{curve.name} assigned to {settings.layer_name}"
        )

        return {'FINISHED'}



#bind target mesh
class AUTOPAINT_OT_bind_target(bpy.types.Operator):
    bl_idname = "autopaint.bind_target"
    bl_label = "Bind Target Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):

        selected = context.selected_objects

        if len(selected) != 2:
            return False

        mesh_found = False
        curve_found = False

        for obj in selected:

            if obj.type == 'MESH':
                mesh_found = True

            elif obj.type == 'CURVE':
                curve_found = True

        return mesh_found and curve_found

    def execute(self, context):

        mesh_obj = None
        curve_obj = None

        for obj in context.selected_objects:

            if obj.type == 'MESH':
                mesh_obj = obj

            elif obj.type == 'CURVE':
                curve_obj = obj

        if mesh_obj is None:
            self.report(
                {'ERROR'},
                "No mesh selected"
            )
            return {'CANCELLED'}

        if curve_obj is None:
            self.report(
                {'ERROR'},
                "No curve selected"
            )
            return {'CANCELLED'}

        curve_obj["ap_target_mesh"] = mesh_obj.name

        self.report(
            {'INFO'},
            f"{curve_obj.name} -> {mesh_obj.name}"
        )

        return {'FINISHED'}


class AUTOPAINT_OT_sample_curve(bpy.types.Operator):

    bl_idname = "autopaint.sample_curve"
    bl_label = "Sample Curve"

    def execute(self, context):

        settings = context.scene.settings

        curve = context.active_object

        #check if curve is not CURVE
        if curve is None or curve.type != 'CURVE':

            self.report(
                {'ERROR'},
                "Select Curve"
            )

            return {'CANCELLED'}

        points = sample_curve_points(
            curve,
            settings.brush_count
        )

        collection = bpy.data.collections.get(
            "AP_SAMPLES"
        )

        if collection is None:

            collection = bpy.data.collections.new(
                "AP_SAMPLES"
            )

            bpy.context.scene.collection.children.link(
                collection
            )

        for obj in list(collection.objects):
            bpy.data.objects.remove(
                obj,
                do_unlink=True
            )

        for i, p in enumerate(points):

            empty = bpy.data.objects.new(
                f"AP_{i:04d}",
                None
            )
            empty.empty_display_type = 'SPHERE'
            empty.empty_display_size = 0.002
            empty.location = p
            collection.objects.link(empty)

        self.report(
            {'INFO'},
            f"{len(points)} points generated"
        )

        return {'FINISHED'}
class AUTOPAINT_OT_project_points(bpy.types.Operator):

    bl_idname = "autopaint.project_points"
    bl_label = "Project Points"

    def execute(self, context):

        curve = context.active_object

        if curve.type != 'CURVE':
            self.report({'ERROR'}, "Select Curve")
            return {'CANCELLED'}

        mesh_name = curve.get("ap_target_mesh")

        if not mesh_name:
            self.report({'ERROR'}, "Curve not bound")
            return {'CANCELLED'}

        mesh_obj = bpy.data.objects.get(mesh_name)

        settings = context.scene.settings

        points = sample_curve_points(
            curve,
            settings.brush_count
        )

        hits = project_points_to_mesh(
            mesh_obj,
            points
        )

        print("================================")
        print("TOTAL POINTS:", len(points))
        print("TOTAL HITS:", len(hits))
        print("================================")

        for h in hits[:10]:

            print(
                "FACE:",
                h["face_index"],
                "POS:",
                h["world_location"]
            )

        self.report(
            {'INFO'},
            f"{len(hits)} hits found"
        )

        return {'FINISHED'}
class AUTOPAINT_OT_debug_uv(bpy.types.Operator):

    bl_idname = "autopaint.debug_uv"
    bl_label = "Debug UV"

    def execute(self, context):

        curve = context.active_object

        if curve.type != 'CURVE':

            self.report(
                {'ERROR'},
                "Select Curve"
            )

            return {'CANCELLED'}

        mesh_name = curve.get(
            "ap_target_mesh"
        )

        mesh_obj = bpy.data.objects.get(
            mesh_name
        )

        settings = context.scene.settings

        points = sample_curve_points(
            curve,
            settings.brush_count
        )

        hits = project_points_to_mesh(
            mesh_obj,
            points
        )

        print("========== UV TEST ==========")

        count = 0
        image = bpy.data.images.get("AP_IMG_1")

        for hit in hits:

            print("FACE =", hit["face_index"])

            uv = get_uv_from_hit(
                mesh_obj,
                hit
            )
            self.report({'INFO'}, f"UV = {uv}")
            if uv:
                print("IMAGE =", image)
                px, py = uv_to_pixel(   
                    image,
                    uv
                )
                paint_pixel(
                        image,
                        px,
                        py,
                        settings.brush_color
                )

                count += 1

        self.report(
            {'INFO'},
            f"TOTAL HITS: {len(hits)}"
        )
        self.report(
            {'INFO'},
            f"{count} UVs"
        )
      

        return {'FINISHED'}

#---------------------------
class AUTOPAINT_OT_paint_curve(bpy.types.Operator):

    bl_idname = "autopaint.paint_curve"
    bl_label = "Paint Curve"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):

        selected = context.selected_objects

        if len(selected) != 2:
            return False

        mesh_found = False
        curve_found = False

        for obj in selected:

            if obj.type == 'MESH':
                mesh_found = True

            elif obj.type == 'CURVE':
                curve_found = True

        return mesh_found and curve_found

    def execute(self, context):
        mesh_obj = None
        curve_obj = None

        for obj in context.selected_objects:

            if obj.type == 'MESH':
                mesh_obj = obj

            elif obj.type == 'CURVE':
                curve_obj = obj

        if mesh_obj is None:
            self.report(
                {'ERROR'},
                "No mesh selected"
            )
            return {'CANCELLED'}

        if curve_obj is None:
            self.report(
                {'ERROR'},
                "No curve selected"
            )
            return {'CANCELLED'}

        curve_obj["ap_target_mesh"] = mesh_obj.name
        
        mesh_name = curve_obj.get("ap_target_mesh")

        if not mesh_name:

            self.report({'ERROR'}, "Curve has no target mesh")
            return {'CANCELLED'}

        mesh_obj = bpy.data.objects.get(mesh_name)

        if mesh_obj is None:

            self.report({'ERROR'}, "Target mesh not found")
            return {'CANCELLED'}

        image = bpy.data.images.get("AP_IMG_1")

        if image is None:

            self.report({'ERROR'}, "AP_IMG_1 not found")

            return {'CANCELLED'}

        settings = context.scene.settings

        points = sample_curve_points(
            curve_obj,
            settings.brush_count
        )

        print("CURVE POINTS =", len(points))

        hits = project_points_to_mesh(
            mesh_obj,
            points
        )
        print("HITS =", len(hits))
        width = image.size[0]
        height = image.size[1]

        pixels = list(
            image.pixels
        )

        color = curve_obj.get(
            "ap_color",
            settings.brush_color
        )
        opacity = curve_obj.get(
            "ap_opacity",
            settings.brush_opacity
        )

        strength = curve_obj.get(
            "ap_strength",
            settings.brush_strength
        )

        falloff = curve_obj.get(
            "ap_falloff",
            settings.brush_falloff
        )
        radius = int(
            curve_obj.get(
                "ap_size",
                settings.brush_size
            )
        )

        painted = 0
        uv_list = []
        for hit in hits:

            uv = get_uv_from_hit(
                mesh_obj,
                hit
            )
            if uv is None:
                continue

            uv_list.append(uv)

        painted = 0

        brush = settings.brush_image
        
        print("UV COUNT =",len(uv_list))

        for uv in uv_list:

            px, py = uv_to_pixel(
                image,
                uv
            )
            print(px, py)
            if brush:

                paint_brush_on_image(
                    pixels,
                    width,
                    height,
                    px,
                    py,
                    brush,
                    settings.brush_size,
                    color,
                    opacity
                )

            else:

                paint_circle_on_image(
                    pixels,
                    width,
                    height,
                    px,
                    py,
                    radius,
                    color,
                    opacity,
                    strength,
                    falloff
                )

            painted += 1
            image.pixels[:] = pixels
            image.update()
        print(image.pixels[0],
        image.pixels[1],
        image.pixels[2],
        image.pixels[3])

        self.report(
            {'INFO'},
            f"{painted} brush stamps painted"
        )

        return {'FINISHED'}


class AUTOPAINT_OT_clear_image(bpy.types.Operator):
    bl_idname = "autopaint.clear_image"
    bl_label = "Clear Paint"

    def execute(self, context):

        image = bpy.data.images.get(
            "AP_IMG_1"
        )

        if image is None:

            self.report(
                {'ERROR'},
                "AP_IMG_1 not found"
            )

            return {'CANCELLED'}

        pixels = [0.0] * (
            image.size[0] *
            image.size[1] *
            4
        )

        image.pixels[:] = pixels
        image.update()

        self.report(
            {'INFO'},
            "Image Cleared"
        )

        return {'FINISHED'}



class MESH_OT_add_cube_button(bpy.types.Operator):
    bl_idname = "mesh.add_cube_button"
    bl_label = "Add Cube"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # This calls Blender's built-in operator to add a primitive cube
        #bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, 0))
        return {'FINISHED'}







# register-------------------------------
classes = (AUTOPAINT_OT_generate_path, 
            AUTOPAINT_OT_start_curve_draw, 
            AUTOPAINT_OT_init_core, 
            AUTOPAINT_OT_delete_layer, 
            AUTOPAINT_OT_add_layer,
            AUTOPAINT_OT_toggle_layer, 
            Shader_OT_Diamond,
            AUTOPAINT_OT_apply_to_layer,
            AUTOPAINT_OT_bind_target, 
            AUTOPAINT_OT_sample_curve,
            AUTOPAINT_OT_project_points,
            AUTOPAINT_OT_debug_uv,
            AUTOPAINT_OT_paint_curve,
            MESH_OT_add_cube_button,
            AUTOPAINT_OT_clear_image

            )

def register():
    """Register operators"""
    for cls in classes:
        bpy.utils.register_class(cls)
    print("Operators registered!")

def unregister():
    """Unregister operators"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("Operators unregistered!")