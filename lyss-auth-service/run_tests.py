#!/usr/bin/env python3
"""
测试运行器脚本

提供便捷的测试执行入口，支持不同的测试模式和配置。
包含单元测试、集成测试、覆盖率报告等功能。

Author: Lyss AI Team  
Created: 2025-01-21
Modified: 2025-01-21
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_command(cmd, description=""):
    """运行命令并处理输出"""
    print(f"\n{'='*60}")
    if description:
        print(f"🔍 {description}")
    print(f"📋 执行命令: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description or '命令'} 执行成功!")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ {description or '命令'} 执行失败! 退出码: {e.returncode}")
        return False
    except Exception as e:
        print(f"💥 执行异常: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Auth Service 测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python run_tests.py                    # 运行所有测试
  python run_tests.py --unit            # 仅运行单元测试
  python run_tests.py --integration     # 仅运行集成测试
  python run_tests.py --fast            # 快速测试（跳过慢速测试）
  python run_tests.py --coverage        # 生成覆盖率报告
  python run_tests.py --verbose         # 详细输出
  python run_tests.py --specific auth   # 运行特定模块测试
        """
    )
    
    # 测试类型选项
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument(
        "--unit", 
        action="store_true", 
        help="仅运行单元测试"
    )
    test_group.add_argument(
        "--integration", 
        action="store_true", 
        help="仅运行集成测试"
    )
    test_group.add_argument(
        "--api", 
        action="store_true", 
        help="仅运行API测试"
    )
    
    # 测试选项
    parser.add_argument(
        "--fast", 
        action="store_true", 
        help="快速测试模式（跳过慢速测试）"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true", 
        help="生成覆盖率报告"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="详细输出模式"
    )
    parser.add_argument(
        "--specific", 
        type=str, 
        help="运行特定的测试模块（如: auth, jwt, rbac, mfa等）"
    )
    parser.add_argument(
        "--parallel", "-n", 
        type=int, 
        default=1,
        help="并行测试进程数"
    )
    parser.add_argument(
        "--failfast", "-x", 
        action="store_true", 
        help="第一个失败后立即停止"
    )
    
    args = parser.parse_args()
    
    # 构建pytest命令
    cmd = ["python", "-m", "pytest"]
    
    # 基本选项
    if args.verbose:
        cmd.extend(["-v", "-s"])
    else:
        cmd.append("-v")
    
    if args.failfast:
        cmd.append("-x")
    
    if args.parallel > 1:
        cmd.extend(["-n", str(args.parallel)])
    
    # 测试类型选择
    if args.unit:
        cmd.extend(["-m", "unit"])
        test_desc = "单元测试"
    elif args.integration:
        cmd.extend(["-m", "integration"])
        test_desc = "集成测试"
    elif args.api:
        cmd.extend(["-m", "api"])
        test_desc = "API测试"
    elif args.specific:
        # 运行特定模块的测试
        test_file = f"tests/test_{args.specific}*.py"
        cmd.append(test_file)
        test_desc = f"{args.specific}模块测试"
    else:
        test_desc = "所有测试"
    
    # 快速测试模式
    if args.fast:
        cmd.extend(["-m", "not slow"])
        test_desc += "（快速模式）"
    
    # 覆盖率选项
    if args.coverage:
        cmd.extend([
            "--cov=auth_service",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
            "--cov-fail-under=80"
        ])
        test_desc += " + 覆盖率报告"
    
    # 确保在正确的目录中运行
    os.chdir(Path(__file__).parent)
    
    print("🧪 Auth Service 测试运行器")
    print(f"📍 工作目录: {os.getcwd()}")
    print(f"🎯 测试范围: {test_desc}")
    
    # 检查测试文件是否存在
    test_dir = Path("tests")
    if not test_dir.exists():
        print(f"❌ 测试目录不存在: {test_dir}")
        sys.exit(1)
    
    test_files = list(test_dir.glob("test_*.py"))
    if not test_files:
        print(f"❌ 未找到测试文件: {test_dir}/test_*.py")
        sys.exit(1)
    
    print(f"📁 找到 {len(test_files)} 个测试文件:")
    for test_file in sorted(test_files):
        print(f"   - {test_file.name}")
    
    # 运行测试
    success = run_command(cmd, f"运行{test_desc}")
    
    # 生成测试报告摘要
    if success:
        print(f"\n🎉 测试执行完成!")
        
        if args.coverage:
            print("\n📊 覆盖率报告:")
            print("   - 终端报告: 已显示在上方")
            print("   - HTML报告: htmlcov/index.html")
            print("   - XML报告: coverage.xml")
            
            # 打开HTML覆盖率报告（可选）
            html_report = Path("htmlcov/index.html")
            if html_report.exists():
                print(f"   - 在浏览器中查看: file://{html_report.absolute()}")
    else:
        print(f"\n💔 测试执行失败!")
        sys.exit(1)

if __name__ == "__main__":
    main()