"""Chinese operator prompts paired with RoboDojo's official task instructions."""
import re


PROMPTS_ZH = {
    "align_blocks": "使用直角尺把三个方块推成一条对齐的直线，然后将双臂复位。",
    "arrange_largest_number": "将数字从左到右排列成尽可能大的数，并把每个数字放到对应垫板上。",
    "arrange_largest_number_random": "在干扰物中找到数字，将它们从左到右排列成尽可能大的数，并放到对应垫板上。",
    "build_tower": "使用木块和木板搭建完整且稳定的塔。",
    "classify_objects": "按类别把物体分别放入三个篮筐，完成后将双臂复位。",
    "classify_objects_by_language": "按照本局语言指令，将三类物体分别放入左、中、右篮筐，完成后将双臂复位。",
    "cover_blocks": "从左到右用杯子盖住三个方块并记住颜色，然后依次揭开红、绿、蓝色方块。",
    "deposit_coin": "从托架拿起硬币，将它准确插入存钱罐。",
    "fasten_screws": "把每颗螺钉插入同色螺母并拧紧，完成后松开夹爪并将双臂复位。",
    "fill_egg_holder": "把篮筐中的四枚鸡蛋放进蛋盒，然后合上盒盖并将双臂复位。",
    "fill_pen_holder": "一只手扶住笔筒，另一只手把所有笔插入笔筒，最后把笔筒直立放回桌面。",
    "fold_clothes": "将衣服整齐折叠。",
    "fold_clothes_random": "在随机场景中将衣服整齐折叠。",
    "general_pickup": "将本局目标物体向上拿起 10 厘米。",
    "hang_mugs": "把所有杯子挂到杯架上，完成后将双臂复位。",
    "hang_mugs_random": "在随机场景中把所有杯子挂到杯架上，完成后将双臂复位。",
    "imitate_sorting_sequence": "观察并记住物体进入篮筐的顺序，再按相同顺序把对应物体放入篮筐。",
    "insert_key": "拿起钥匙，交接到另一只手，插入锁孔后转动钥匙。",
    "insert_tubes": "将三根管子逐一插入管架的正确孔位。",
    "make_kong": "等待对手打出一张牌，再用三张相同的牌完成明杠。",
    "make_toast": "拿起两片面包放入烤面包机，然后将压杆按到底。",
    "make_toast_random": "在随机场景中拿起两片面包放入烤面包机，然后将压杆按到底。",
    "match_and_pick_from_conveyor": "记住传送带第一次出现的物体；它再次出现时抓起对应物体。",
    "organize_table": "把鼠标放到鼠标垫上、键盘推入框内、摆件放上支架、闹钟放到抽屉上，再打开抽屉并把其余杂物全部放入。",
    "pack_objects_into_box": "把所有物体装入箱子，并让每个物体的正面朝左。",
    "pack_objects_into_box_random": "在随机场景中把所有物体装入箱子，并让每个物体的正面朝左。",
    "pick_from_conveyor_by_image": "先将篮筐抬高超过 8 厘米；根据板上图片识别目标，从传送带抓起目标并放入篮筐。",
    "play_Xylophone": "拿起琴槌，从左到右依次敲击所有木琴键。",
    "play_stacking_toy": "把所有叠叠乐部件放到各自正确的柱子上。",
    "play_tic_tac_toe": "作为先手与对手完成一局井字棋，并按规则填满棋盘。",
    "plug_in_charger": "将充电器插入插线板插孔。",
    "pour_balls_into_vase": "把杯子中的所有小球倒入花瓶。",
    "pour_by_language": "按照本局颜色顺序，将三只瓶中的液体分别倒入对应的三只碗，然后将双臂复位。",
    "pour_liquid_into_cup": "把瓶中的液体倒入杯子，尽量不要洒出。",
    "pour_liquid_into_cup_random": "在随机场景中把瓶中的液体倒入杯子，尽量不要洒出。",
    "press_by_number": "按照数字卡要求的次数分别按下两个红色按钮，最后按蓝色按钮确认。",
    "push_T": "推动 T 形块，使它与灰色 T 形垫板准确重合，然后将双臂复位。",
    "push_T_random": "在随机场景中推动 T 形块，使它与灰色 T 形垫板准确重合，然后将双臂复位。",
    "put_bottles_into_dustbin": "把所有瓶子投入垃圾桶；够不到时使用双手交接，完成后将双臂复位。",
    "solve_equation": "选择正确的缺失数字或运算符放到空缺垫板上，使等式成立，然后将双臂复位。",
    "sort_nesting_dolls_by_size": "把五个套娃从左到右按从小到大排成一行并保持直立。",
    "sort_nesting_dolls_by_size_random": "在随机场景中把五个套娃从左到右按从小到大排成一行并保持直立。",
    "stack_blocks": "把三个不同纹理的方块稳定堆叠起来，然后将双臂复位。",
    "stack_blocks_by_language": "按照本局指定的颜色顺序，从下到上堆叠三个方块，然后将双臂复位。",
    "stack_blocks_random": "在随机场景中把三个不同纹理的方块稳定堆叠起来，然后将双臂复位。",
    "stack_bowls": "把三个碗保持正向并稳定套叠在一起，然后将双臂复位。",
    "stack_bowls_random": "在随机场景中把三个碗保持正向并稳定套叠在一起，然后将双臂复位。",
    "store_laptop_and_headphones": "把耳机挂到耳机架上，合上笔记本电脑，再将电脑竖直放入收纳架。",
    "store_laptop_and_headphones_random": "在随机场景中把耳机挂到耳机架上，合上笔记本电脑，再将电脑竖直放入收纳架。",
    "store_tools_in_toolbox": "把钳子、锤子、卷尺和扳手分别放入工具箱对应槽位，然后将双臂复位。",
    "swap_T": "拿起两个 T 形块，交换它们的位置，并按原目标姿态放回。",
    "swap_blocks": "利用空垫板交换两个方块的位置，每移动一步后按一次按钮。",
    "sweep_blocks": "拿起扫帚并交接到右手，再配合簸箕把所有方块扫入簸箕。",
    "sweep_blocks_random": "在随机场景中拿起扫帚并交接到右手，再配合簸箕把所有目标物扫入簸箕。",
}


WORDS_ZH = {
    "red": "红色", "green": "绿色", "blue": "蓝色", "yellow": "黄色",
    "orange": "橙色", "cyan": "青色", "turquoise": "青绿色", "violet": "紫色",
    "black": "黑色", "white": "白色", "brown": "棕色", "block": "方块",
    "cube": "方块", "bottle": "瓶子", "bowl": "碗", "cup": "杯子",
    "mug": "马克杯", "apple": "苹果", "banana": "香蕉", "orange fruit": "橙子",
}


def _term_zh(value):
    value = value.strip().lower().replace("_", " ")
    if value in WORDS_ZH:
        return WORDS_ZH[value]
    words = [WORDS_ZH.get(word, word) for word in value.split()]
    translated = "".join(words)
    return translated if all(word in WORDS_ZH for word in value.split()) else f"“{value}”"


def chinese_prompt(task, instruction):
    """Keep dynamic language-task values while presenting an operator prompt in Chinese."""
    instruction = str(instruction).strip()
    if task == "stack_blocks_by_language":
        match = re.search(r"order of\s*([^,]+),\s*([^,]+),\s*and\s*([^,]+),", instruction, re.I)
        if match:
            colors = [_term_zh(value) for value in match.groups()]
            return f"从下到上依次堆叠{colors[0]}、{colors[1]}、{colors[2]}方块，然后将双臂复位。"
    elif task == "classify_objects_by_language":
        match = re.search(r"Put (.+?) objects into the left basket, (.+?) objects into the middle basket, and (.+?) objects into the right basket", instruction, re.I)
        if match:
            categories = [_term_zh(value) for value in match.groups()]
            return (f"将{categories[0]}类物体放入左侧篮筐，{categories[1]}类物体放入中间篮筐，"
                    f"{categories[2]}类物体放入右侧篮筐，然后将双臂复位。")
    elif task == "pour_by_language":
        pairs = re.findall(r"(red|turquoise|violet) bottle.*?(black|white|brown) bowl", instruction, re.I)
        if len(pairs) == 3:
            steps = [f"将{_term_zh(bottle)}瓶中的液体倒入{_term_zh(bowl)}碗" for bottle, bowl in pairs]
            return "；".join(steps) + "，然后将双臂复位。"
    elif task == "general_pickup":
        match = re.search(r"Pick up (?:the )?(.+?) by 10 cm", instruction, re.I)
        if match:
            return f"将{_term_zh(match.group(1))}向上拿起 10 厘米。"
    return PROMPTS_ZH.get(task, f"完成任务：{instruction}")
