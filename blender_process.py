import bpy
import os

# 定义变量

# 功能开关
auto_detect_frame_range = True   # 自动检测帧范围 (True/False)
override_render_settings = False  # 是否使用自定义设置覆盖原本设置，False为使用blender文件原本设置
enable_compositing_setup = True  # 是否启用自定义合成节点设置 (True/False)

# 输出路径设置
base_output_path = "E:\\Code\\Blender_output" # 基础输出目录

# 动画参数 (当 auto_detect_frame_range = False 时生效)
animation_start_frame = 1        # 动画起始帧
animation_end_frame = 100        # 动画结束帧
focal_length_start = 21          # 起始焦距
focal_length_end = 120           # 结束焦距
frame_rate = 25                  # 帧率 (当 override_render_settings = True 时生效)
frame_step = 1                   # 步长

# 渲染质量参数 (当 override_render_settings = True 时生效)
render_max_samples = 128         # 最大采样
render_min_samples = 0           # 最小采样
render_time_limit = 0            # 时间限制
use_light_tree = False           # 灯光树

# 渲染通道参数
enable_pass_combined = True    # 启用合成通道 (默认开启)
enable_pass_z = True           # 启用Z深度通道
enable_pass_mist = True        # 启用雾效通道
enable_pass_position = True      # 启用位置通道

# 色彩管理参数
view_transform_setting = 'Filmic' # 查看变换 ('Standard', 'Filmic', 'Raw', etc.)


# 自动寻找起始帧和结束帧
def find_scene_frame_range():
    min_frame = float('inf')
    max_frame = float('-inf')
    found_keyframes = False
    for action in bpy.data.actions:
        if action.fcurves:
            frame_numbers = [key.co.x for fcurve in action.fcurves for key in fcurve.keyframe_points]
            if frame_numbers:
                found_keyframes = True
                min_frame = min(min_frame, min(frame_numbers))
                max_frame = max(max_frame, max(frame_numbers))
    if found_keyframes:
        return int(round(min_frame)), int(round(max_frame))
    else:
        return None, None

# 合成节点设置函数
def setup_compositing_nodes(main_output_directory):
    print("="*40)
    print("步骤4: 设置自定义合成节点...")
    
    # 获取节点树的引用
    node_tree = bpy.context.scene.node_tree
    if not node_tree:
        print("!!! 错误: 场景未启用合成节点或无法获取节点树。 !!!")
        return
        
    nodes = node_tree.nodes
    links = node_tree.links
    
    # 启用场景的合成节点功能。
    bpy.context.scene.use_nodes = True
    print(" - 已启用场景的合成节点。")
    
    # 调用外部插件的功能来创建和设置文件输出节点。
    try:
        bpy.ops.cpo.add_output(clear_nodes=True)
        print(" - 已成功调用'cpo'插件创建通道输出节点。")
    except AttributeError:
        print("!!! 错误: 无法调用 'bpy.ops.cpo.add_output()'。请确保相关插件已正确安装并启用。 !!!")
        return

    # 断开指定的连接线
    print(" - 正在断开指定的节点连接...")
    
    def disconnect_sockets(from_node, from_socket_name, to_node, to_socket_name):
        from_socket = from_node.outputs.get(from_socket_name)
        to_socket = to_node.inputs.get(to_socket_name)
        if not from_socket or not to_socket: return
        for link in node_tree.links:
            if link.from_socket == from_socket and link.to_socket == to_socket:
                node_tree.links.remove(link)
                print(f"   - 已断开: {from_node.name}['{from_socket_name}'] -> {to_node.name}['{to_socket_name}']")
                return
    
    render_layers_node = None
    file_output_node = None
    for node in node_tree.nodes:
        if node.type == 'R_LAYERS': render_layers_node = node
        elif node.type == 'OUTPUT_FILE': file_output_node = node
            
    # 执行断开
    if render_layers_node and file_output_node:
        disconnect_sockets(render_layers_node, 'Alpha', file_output_node, 'Alpha')
        disconnect_sockets(render_layers_node, 'Depth', file_output_node, 'Depth')
    else:
        print("!!! 错误: 找不到'渲染层'或'文件输出'节点，无法执行断开操作。 !!!")


    # 添加新的节点
    print(" - 正在添加新的合成节点...")

    normalize_node = nodes.new(type='CompositorNodeNormalize')
    normalize_node.location = (300, 200) 
    print(f"   - 已创建节点: {normalize_node.name} (类型: Normalize)")

    combine_color_node = nodes.new(type='CompositorNodeCombineColor')
    combine_color_node.mode = 'RGB'
    combine_color_node.location = (500, 200)
    print(f"   - 已创建节点: {combine_color_node.name} (类型: Combine Color, 模式: RGB)")

    # 创建新的连接
    print(" - 正在创建新的节点连接...")
            
    if render_layers_node and file_output_node and normalize_node and combine_color_node:
        links.new(render_layers_node.outputs['Depth'], normalize_node.inputs['Value'])
        print(f"   - 已连接: Render Layers['Depth'] -> Normalize['Value']")
        
        links.new(normalize_node.outputs['Value'], combine_color_node.inputs['Red'])
        print(f"   - 已连接: Normalize['Value'] -> Combine Color['Red']")

        links.new(normalize_node.outputs['Value'], combine_color_node.inputs['Green'])
        print(f"   - 已连接: Normalize['Value'] -> Combine Color['Green']")

        links.new(normalize_node.outputs['Value'], combine_color_node.inputs['Blue'])
        print(f"   - 已连接: Normalize['Value'] -> Combine Color['Blue']")

        depth_input_socket = file_output_node.inputs.get('Depth')
        if depth_input_socket:
            links.new(combine_color_node.outputs['Image'], depth_input_socket)
            print(f"   - 已连接: Combine Color['Image'] -> File Output['Depth']")
        else:
            print("!!! 错误: 在文件输出节点上找不到名为 'Depth' 的输入接口。 !!!")
    else:
        print("!!! 错误: 找不到所有必需的节点，无法执行连接操作。 !!!")

    # 设置文件输出节点的属性
    print(" - 正在设置文件输出节点的属性...")
    if file_output_node:
        # 为通道文件创建一个名为 "passes" 的子文件夹
        passes_directory = os.path.join(main_output_directory, "passes")
        os.makedirs(passes_directory, exist_ok=True)
        file_output_node.base_path = passes_directory
        print(f"   - 文件输出节点路径设置为: {passes_directory}")

        file_output_node.format.file_format = 'TIFF'
        file_output_node.format.color_depth = '16'
        # file_output_node.format.compression = 'ZIP'
        bpy.data.scenes["Scene"].node_tree.nodes["CPO File Output (Scene/ViewLayer)"].format.exr_codec = 'ZIP'

        
        print(f"   - 文件输出节点格式: {file_output_node.format.file_format}, "
              f"色深: {file_output_node.format.color_depth}-bit, "
              f"压缩: {file_output_node.format.compression}")
    else:
        print("!!! 错误: 找不到文件输出节点，无法设置其属性。 !!!")
    
    print(" - 合成节点设置完成。")
    print("="*40)


# 主脚本

# 获取场景和渲染设置的引用
scene = bpy.context.scene
render_settings = scene.render

# 渲染与场景设置
print("="*40)
print("步骤1: 设置渲染和场景参数...")
render_settings.engine = 'CYCLES'
scene.cycles.device = 'GPU'

# 动画范围设置
if auto_detect_frame_range:
    print(" - 模式: 自动检测帧范围...")
    start, end = find_scene_frame_range()
    if start is not None:
        scene.frame_start = start
        scene.frame_end = end
    else:
        scene.frame_start = animation_start_frame
        scene.frame_end = animation_end_frame
        print(f" - 警告: 未找到任何关键帧，已退回手动设置范围: {scene.frame_start} - {scene.frame_end} 帧")
else:
    print(" - 模式: 手动设置帧范围...")
    scene.frame_start = animation_start_frame
    scene.frame_end = animation_end_frame

# 步长总是由脚本设置
scene.frame_step = frame_step

# 根据开关决定是否覆盖渲染质量和帧率
cycles_settings = scene.cycles
if override_render_settings:
    print(" - 模式: 覆盖渲染质量与帧率设置...")
    render_settings.fps = frame_rate
    cycles_settings.samples = render_max_samples
    cycles_settings.adaptive_min_samples = render_min_samples
    cycles_settings.time_limit = render_time_limit
else:
    print(" - 模式: 使用.blend文件原始渲染质量与帧率设置。")

# 以下设置总是由脚本控制
cycles_settings.use_light_tree = use_light_tree
scene.view_settings.view_transform = view_transform_setting

# 设置渲染通道
print(" - 设置渲染通道...")
for view_layer in scene.view_layers:
    if view_layer.use:
        view_layer.use_pass_combined = enable_pass_combined
        view_layer.use_pass_z = enable_pass_z
        view_layer.use_pass_mist = enable_pass_mist
        view_layer.use_pass_position = enable_pass_position
print(f"   - Z-Depth: {enable_pass_z}, Mist: {enable_pass_mist}, Position: {enable_pass_position}")

# 在系统控制台打印最终生效的反馈信息
print("\n--- 最终生效参数总览 ---")
print(f" - 动画范围: {scene.frame_start} - {scene.frame_end} 帧, 步长: {scene.frame_step}")
print(f" - 帧率: {render_settings.fps} fps")
print(f" - 采样设置: Max={cycles_settings.samples}, Min={cycles_settings.adaptive_min_samples}, Time Limit={cycles_settings.time_limit}s")
print(f" - 灯光树(Light Tree): {'启用' if cycles_settings.use_light_tree else '禁用'}")
print(f" - 查看变换(View Transform): {scene.view_settings.view_transform}")
print("--- 总览结束 ---\n")
print(" - 渲染设置完成。")
print("="*40)


# 摄像机与动画设置
print("步骤2: 设置摄像机动画...")
camera_obj = scene.camera 

if camera_obj:
    print(f" - 找到活动摄像机: '{camera_obj.name}'")
    camera_data = camera_obj.data

    # 创建焦距动画的关键帧
    camera_data.lens = focal_length_start
    camera_data.keyframe_insert(data_path="lens", frame=scene.frame_start)
    
    camera_data.lens = focal_length_end
    camera_data.keyframe_insert(data_path="lens", frame=scene.frame_end)
    print(" - 已为焦距创建关键帧。")

    # 设置动画插值为线性
    if camera_data.animation_data and camera_data.animation_data.action:
        fcurve = camera_data.animation_data.action.fcurves.find("lens")
        if fcurve:
            for keyframe_point in fcurve.keyframe_points:
                keyframe_point.interpolation = 'LINEAR'
            print(" - 焦距动画的插值已设置为线性。")
    
    print(" - 摄像机动画设置完毕。")

else:
    print("!!! 错误: 此场景没有设置活动摄像机！脚本无法继续 !!!")

print("="*40)


# 3. 输出设置
print("步骤3: 设置输出路径和格式...")

# 获取当前Blender文件的路径
blend_file_path = bpy.data.filepath

# 检查文件是否已保存
if not blend_file_path:
    project_name = "Untitled_Render"
    print(f" - 警告: Blender文件未保存，将使用默认文件夹 '{project_name}'")
else:
    project_name = os.path.basename(os.path.splitext(blend_file_path)[0])
    print(f" - 检测到Blender项目名: {project_name}")

output_directory = os.path.join(base_output_path, project_name)

try:
    os.makedirs(output_directory, exist_ok=True)
    print(f" - 输出目录已设置为: {output_directory}")

    render_settings.filepath = os.path.join(output_directory, "frame_")

    image_settings = render_settings.image_settings
    image_settings.file_format = 'TIFF'
    image_settings.color_mode = 'RGBA'
    image_settings.color_depth = '16'

    print(f" - 输出格式: {image_settings.file_format}, 色彩: {image_settings.color_mode}, 色深: {image_settings.color_depth}-bit")
    print(" - 输出设置完成。")

except Exception as e:
    print(f"!!! 错误: 创建输出目录或设置路径时发生错误: {e} !!!")
    print("!!! 请检查 base_output_path 变量是否为有效且可访问的路径 !!!")

print("="*40)

# 根据开关，调用合成节点设置函数
if enable_compositing_setup:
    # 将主脚本计算出的输出目录传递给函数
    setup_compositing_nodes(output_directory)


# 准备渲染
print("\n所有设置已完成，准备渲染！")

