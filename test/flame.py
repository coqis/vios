import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches


def plot_flamegraph(data, filename='import_flamegraph.png'):
    fig, ax = plt.subplots(figsize=(12, 6))

    # 用于确定Y轴（层级）
    max_depth = 0

    def draw_node(node, x_offset, depth):
        nonlocal max_depth
        name = node['name']
        total = node['total_time']
        self_time = node['self_time']
        children = node.get('children', [])

        max_depth = max(max_depth, depth)

        # 画当前模块的矩形（累计时间）
        rect = patches.Rectangle(
            (x_offset, -depth), total, 1, facecolor='orange', edgecolor='black', alpha=0.7)
        ax.add_patch(rect)
        ax.text(x_offset + total / 2, -depth + 0.5,
                f"{name}\n{total:.3f}s", ha='center', va='center', fontsize=8)

        # 子模块逐个堆叠
        child_x = x_offset
        for child in children:
            draw_node(child, child_x, depth + 1)
            child_x += child['total_time']  # 横向平铺

    # 起始位置为x=0
    x_cursor = 0
    for root in data:
        draw_node(root, x_cursor, depth=0)
        x_cursor += root['total_time'] + 0.1  # 间隔

    ax.set_xlim(0, x_cursor)
    ax.set_ylim(-max_depth - 1, 1)
    ax.set_xlabel("Import Time (seconds)")
    ax.set_ylabel("Module Depth")
    ax.set_title("Python Import Flamegraph (Cumulative Time)")
    ax.axis("off")

    plt.tight_layout()
    plt.savefig(filename)
    print(f"[✓] Flamegraph saved as {filename}")
    plt.show()


if __name__ == "__main__":
    with open("import_times.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    plot_flamegraph(data)
