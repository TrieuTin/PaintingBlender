import bpy
PREFIX = "AP_"
# MATERIAL =====================================
def safe_get_material(obj):
    if not obj.data.materials:
        mat = bpy.data.materials.new(name=f"{PREFIX}Material")
        obj.data.materials.append(mat)
    else:
        mat = obj.data.materials[0]

    mat.use_nodes = True
    return mat
#================================================
#Core ============================================
def setup_initial_pbr_network(node_tree):
    nodes = node_tree.nodes
    links = node_tree.links
    
    principled = None
    output = None

    for n in nodes:
        if n.type == 'BSDF_PRINCIPLED':
            principled = n
        if n.type == 'OUTPUT_MATERIAL':
            output = n

    if not principled:
        principled = nodes.new(type='ShaderNodeBsdfPrincipled')
        principled.location = (300, 0)

    if not output:
        output = nodes.new(type='ShaderNodeOutputMaterial')
        output.location = (600, 0)

    if not output.inputs['Surface'].is_linked:
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])

    return principled
#================================================

#Grouping operators =============================
def create_layer_group(group_name):
    #search old group and delete it
    if group_name in bpy.data.node_groups:
        old_group = bpy.data.node_groups[group_name]
        bpy.data.node_groups.remove(old_group)

    group = bpy.data.node_groups.new(name=group_name, type='ShaderNodeTree')

    group.interface.new_socket(name="Base Color", in_out='INPUT', socket_type='NodeSocketColor')
    group.interface.new_socket(name="Paint Color", in_out='INPUT', socket_type='NodeSocketColor')
    group.interface.new_socket(name="Paint Alpha", in_out='INPUT', socket_type='NodeSocketFloat')

    opacity_socket = group.interface.new_socket(name="Opacity", in_out='INPUT', socket_type='NodeSocketFloat')
    opacity_socket.min_value = 0.0
    opacity_socket.max_value = 1.0
    opacity_socket.default_value = 1.0

    group.interface.new_socket(name="Result", in_out='OUTPUT', socket_type='NodeSocketColor')

    g_nodes = group.nodes
    g_links = group.links

    input_node = g_nodes.new('NodeGroupInput')
    input_node.location = (-600, 0)

    output_node = g_nodes.new('NodeGroupOutput')
    output_node.location = (500, 0)

    alpha_multiply = g_nodes.new('ShaderNodeMath')
    alpha_multiply.operation = 'MULTIPLY'
    alpha_multiply.location = (-250, -150)

    mix_node = g_nodes.new('ShaderNodeMix')
    mix_node.name = "INTERNAL_MIX"
    mix_node.data_type = 'RGBA'
    mix_node.blend_type = 'MIX'
    mix_node.location = (100, 0)

    mix_node.inputs['Factor'].default_value = 1.0

    g_links.new(input_node.outputs['Base Color'], mix_node.inputs['A'])
    g_links.new(input_node.outputs['Paint Color'], mix_node.inputs['B'])

    g_links.new(input_node.outputs['Paint Alpha'], alpha_multiply.inputs[0])
    g_links.new(input_node.outputs['Opacity'], alpha_multiply.inputs[1])
    g_links.new(alpha_multiply.outputs[0], mix_node.inputs['Factor'])

    g_links.new(mix_node.outputs['Result'], output_node.inputs['Result'])

    return group
#================================================