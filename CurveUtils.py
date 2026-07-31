from bl_ui import space_toolsystem_toolbar
import bpy
from mathutils import Vector
from mathutils.geometry import interpolate_bezier, barycentric_transform, intersect_point_tri


def sample_curve_points(curve_obj, count=30):

    all_points = []

    world = curve_obj.matrix_world
    if curve_obj.type == 'CURVE':
        for spline in curve_obj.data.splines:

            if spline.type != 'BEZIER':
                continue

            bezier_points = spline.bezier_points

            for i in range(len(bezier_points) - 1):

                p1 = world @ bezier_points[i].co
                h1 = world @ bezier_points[i].handle_right

                p2 = world @ bezier_points[i + 1].co
                h2 = world @ bezier_points[i + 1].handle_left

                segment = interpolate_bezier(
                    p1,
                    h1,
                    h2,
                    p2,
                    count
                )

                if i > 0:
                    segment = segment[1:]

                all_points.extend(segment)
    else:
        return None

    if len(all_points) <= count:
        return all_points

    result = []

    last = len(all_points) - 1

    for i in range(count):

        idx = round(
            i * last / (count - 1)
        )

        result.append(
            all_points[idx]
        )
    
    return result
# =====================================================
# PROJECTION
def project_points_to_mesh(mesh_obj, points):

    depsgraph = bpy.context.evaluated_depsgraph_get()

    bpy.context.view_layer.update()

    eval_obj = mesh_obj.evaluated_get(
        depsgraph
    )

    mw = eval_obj.matrix_world
    mw_inv = mw.inverted()

    results = []

    for p in points:

        local_point = mw_inv @ p

        success, hit_location, normal, face_index = (
            eval_obj.closest_point_on_mesh(
                local_point
            )
        )

        if success:

            results.append({
                "world_location": mw @ hit_location,
                "local_location": hit_location.copy(),
                "normal": normal.copy(),
                "face_index": face_index
            })

    return results
# =====================================================
def get_uv_from_hit(mesh_obj, hit):

    mesh = mesh_obj.data

    uv_layer = mesh.uv_layers.active

    if uv_layer is None:
        return None

    uv_data = uv_layer.data

    poly = mesh.polygons[
        hit["face_index"]
    ]

    loc = hit["local_location"]

    ls = poly.loop_start

    v1 = mesh.vertices[
        mesh.loops[ls].vertex_index
    ].co

    uv1 = Vector((
        uv_data[ls].uv.x,
        uv_data[ls].uv.y,
        0.0
    ))

    for j in range(1, poly.loop_total - 1):

        i2 = ls + j
        i3 = ls + j + 1

        v2 = mesh.vertices[mesh.loops[i2].vertex_index].co
        v3 = mesh.vertices[mesh.loops[i3].vertex_index].co

        uv2 = Vector((uv_data[i2].uv.x, uv_data[i2].uv.y, 0.0))
        uv3 = Vector((uv_data[i3].uv.x, uv_data[i3].uv.y, 0.0))      
        
        pt = intersect_point_tri(
            loc,
            v1,
            v2,
            v3
        )

        if pt is None:
            continue

        uv = barycentric_transform(
            loc,
            v1,
            v2,
            v3,
            uv1,
            uv2,
            uv3
        )
        return (
            uv.x,
            uv.y
        )

    # fallback triangle

    if poly.loop_total >= 3:

        i2 = ls + 1
        i3 = ls + 2

        v2 = mesh.vertices[
            mesh.loops[i2].vertex_index
        ].co

        v3 = mesh.vertices[
            mesh.loops[i3].vertex_index
        ].co

        uv2 = Vector((
            uv_data[i2].uv.x,
            uv_data[i2].uv.y,
            0.0
        ))

        uv3 = Vector((
            uv_data[i3].uv.x,
            uv_data[i3].uv.y,
            0.0
        ))

        uv = barycentric_transform(
            loc,
            v1,
            v2,
            v3,
            uv1,
            uv2,
            uv3
        )

        return (
            uv.x,
            uv.y
        )

    return None

# =====================================================
def uv_to_pixel(image, uv):

    width = image.size[0]
    height = image.size[1]

    x = int(uv[0] * (width - 1))
    y = int(uv[1] * (height - 1))

    return x, y

def paint_pixel(
    image,
    px,
    py,
    color
):

    width = image.size[0]
    height = image.size[1]

    if px < 0 or px >= width:
        return

    if py < 0 or py >= height:
        return

    index = (py * width + px) * 4

    pixels = list(image.pixels)

    pixels[index + 0] = color[0]
    pixels[index + 1] = color[1]
    pixels[index + 2] = color[2]
    pixels[index + 3] = color[3]

    image.pixels[:] = pixels

    image.update()
    #--------------------------------
def paint_circle_on_image(
    pixels,
    width,
    height,
    center_x,
    center_y,
    radius,
    color,
    opacity=1.0,
    strength=1.0,
    falloff=1.0
):

    r2 = radius * radius

    min_x = max(
        0,
        center_x - radius
    )

    max_x = min(
        width - 1,
        center_x + radius
    )

    min_y = max(
        0,
        center_y - radius
    )

    max_y = min(
        height - 1,
        center_y + radius
    )

    for y in range(
        min_y,
        max_y + 1
    ):

        for x in range(
            min_x,
            max_x + 1
        ):

            dx = x - center_x
            dy = y - center_y

            dist2 = dx * dx + dy * dy

            if dist2 > r2:
                continue

            dist = (dist2 ** 0.5) / radius

            weight = (
                1.0 - dist
            ) ** falloff

            alpha = (
                opacity *
                strength *
                weight
            )

            idx = (
                (y * width + x)
                * 4
            )

            blend_pixel(
                pixels,
                idx,
                color,
                alpha
            )

def blend_pixel(pixels,idx,color,alpha):
    old_r = pixels[idx + 0]
    old_g = pixels[idx + 1]
    old_b = pixels[idx + 2]
    old_a = pixels[idx + 3]

    pixels[idx + 0] = old_r * (1.0 - alpha) + color[0] * alpha
    pixels[idx + 1] = old_g * (1.0 - alpha) + color[1] * alpha
    pixels[idx + 2] = old_b * (1.0 - alpha) + color[2] * alpha
    pixels[idx + 3] = max(
        old_a,
        color[3] * alpha
    )
def paint_uv_line(
    pixels,
    width,
    height,
    uv1,
    uv2,
    radius,
    color,
    opacity,
    strength,
    falloff
):

    dx = uv2[0] - uv1[0]
    dy = uv2[1] - uv1[1]

    dist = (dx * dx + dy * dy) ** 0.5

    spacing = max(
        1,
        radius // 2
    )

    pixel_dist = dist * width

    steps = max(
        1,
        int(pixel_dist / spacing)
    )

    for i in range(steps + 1):

        t = i / steps

        u = uv1[0] + dx * t
        v = uv1[1] + dy * t

        px = int(u * (width - 1))
        py = int(v * (height - 1))

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

def paint_brush_on_image(
    pixels,
    width,
    height,
    center_x,
    center_y,
    brush_image,
    brush_size,
    color,
    opacity=1.0
):
    if brush_image is None:
        return

    brush_pixels = list(
        brush_image.pixels[:]
    )

    src_w = brush_image.size[0]
    src_h = brush_image.size[1]

    # Kích thước brush sau khi scale
    dst_w = max(
        1,
        int(brush_size)
    )

    dst_h = max(
        1,
        int(brush_size)
    )

    start_x = center_x - dst_w // 2
    start_y = center_y - dst_h // 2

    painted = 0

    for y in range(dst_h):

        for x in range(dst_w):

            # Sample từ brush gốc
            src_x = int(
                (x / dst_w) * src_w
            )

            src_y = int(
                (y / dst_h) * src_h
            )

            src_x = min(
                src_x,
                src_w - 1
            )

            src_y = min(
                src_y,
                src_h - 1
            )

            brush_index = (
                (src_y * src_w + src_x)
                * 4
            )

            br = brush_pixels[
                brush_index + 0
            ]

            bg = brush_pixels[
                brush_index + 1
            ]

            bb = brush_pixels[
                brush_index + 2
            ]

            ba = brush_pixels[
                brush_index + 3
            ]

            if ba <= 0.001:
                continue

            px = start_x + x
            py = start_y + y

            if (
                px < 0 or
                px >= width or
                py < 0 or
                py >= height
            ):
                continue

            img_index = (
                (py * width + px)
                * 4
            )

            alpha = ba * opacity

            pixels[
                img_index + 0
            ] = (
                pixels[
                    img_index + 0
                ] * (1.0 - alpha)
                + br * color[0] * alpha
            )

            pixels[
                img_index + 1
            ] = (
                pixels[
                    img_index + 1
                ] * (1.0 - alpha)
                + bg * color[1] * alpha
            )

            pixels[
                img_index + 2
            ] = (
                pixels[
                    img_index + 2
                ] * (1.0 - alpha)
                + bb * color[2] * alpha
            )

            pixels[
                img_index + 3
            ] = max(
                pixels[
                    img_index + 3
                ],
                alpha
            )

            painted += 1

    print(
        f"STAMP PIXELS = {painted}"
    )
def clear_image(image):
    image.pixels[:] = [0.0] * (image.width * image.height * 4)
    image.update()
    print ("Clear image")