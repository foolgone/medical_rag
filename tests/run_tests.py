"""快速测试脚本"""
import subprocess
import sys
import time


def run_test(test_file, description):
    """运行单个测试"""
    print(f"\n{'=' * 60}")
    print(f"运行测试: {description}")
    print(f"{'=' * 60}")

    result = subprocess.run(
        [sys.executable, test_file],
        cwd="tests"
    )

    return result.returncode == 0


def main():
    print("\n" + "=" * 60)
    print("🧪 医疗Agent系统测试套件")
    print("=" * 60)

    # 测试1: 前端组件
    success1 = run_test("test_frontend.py", "前端组件测试")

    # 测试2: Agent工具
    success2 = run_test("test_agent.py", "Agent工具测试")

    # 提示启动后端
    print("\n" + "=" * 60)
    print("⚠️  接下来需要启动后端服务")
    print("请打开新终端执行: python main.py")
    print("启动后按回车继续API测试...")
    print("=" * 60)
    input()

    # 测试3: API接口
    success3 = run_test("test_api.py", "API接口测试")

    # 测试4: 完整流程
    success4 = run_test("test_complete.py", "完整流程测试")

    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    print(f"前端组件: {'✅ 通过' if success1 else '❌ 失败'}")
    print(f"Agent工具: {'✅ 通过' if success2 else '❌ 失败'}")
    print(f"API接口: {'✅ 通过' if success3 else '❌ 失败'}")
    print(f"完整流程: {'✅ 通过' if success4 else '❌ 失败'}")

    all_passed = success1 and success2 and success3 and success4
    if all_passed:
        print("\n🎉 所有测试通过！系统可以正常使用！")
    else:
        print("\n⚠️  部分测试失败，请检查错误信息")


if __name__ == "__main__":
    main()
