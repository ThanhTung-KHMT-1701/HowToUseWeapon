"""
main.py - Entry point cho VibeGaming
Yêu cầu: conda activate ThiGiacMayTinh
"""

import sys
import os

# Thêm thư mục gốc vào path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("=" * 55)
    print("  VibeGaming - Gesture Combat")
    print("  Điều khiển bằng cử chỉ tay + khẩu hình miệng")
    print("=" * 55)
    print()
    print("  Cử chỉ vũ khí:")
    print("  [1] Găng tay  - Nắm 2 tay, thế boxing")
    print("  [2] Kiếm      - 2 nắm ngang rồi kéo 1 tay ra xa")
    print("  [3] Cung      - 2 nắm dọc rồi kéo 1 tay + bật ngón")
    print("  [4] Lựu đạn  - Nắm 1 tay, di chuyển rồi mở tay")
    print("  [5] Súng      - Ngón trỏ+giữa duỗi 2 tay, nhấn SPACE để bắn")
    print()
    print("  Phím tắt (debug):")
    print("  1-5  = đổi vũ khí")
    print("  D    = hiện debug info")
    print("  R    = restart (khi game over)")
    print("  ESC  = thoát")
    print()

    try:
        from src.game import Game
        game = Game()
        game.run()
    except ImportError as e:
        print(f"[ERROR] Thiếu thư viện: {e}")
        print("Hãy chạy: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"[ERROR] {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
