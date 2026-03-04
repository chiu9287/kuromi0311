import time


try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False

    class GPIO:
        BCM = "BCM"
        OUT = "OUT"
        HIGH = 1
        LOW = 0

        @staticmethod
        def setmode(mode):
            print(f"[MOCK GPIO] setmode({mode})")

        @staticmethod
        def setwarnings(flag):
            print(f"[MOCK GPIO] setwarnings({flag})")

        @staticmethod
        def setup(pin, mode):
            print(f"[MOCK GPIO] setup(pin={pin}, mode={mode})")

        @staticmethod
        def output(pin, state):
            level = "HIGH" if state else "LOW"
            print(f"[MOCK GPIO] output(pin={pin}, state={level})")

        @staticmethod
        def cleanup():
            print("[MOCK GPIO] cleanup()")


PIN_DI0 = 16
PIN_DI1 = 20
PIN_DI2_TRIGGER = 21


class SignalTester:
    def __init__(self):
        self.active_high = True
        self.settle_ms = 200
        self.pulse_ms = 300
        self.hold_ms = 200
        self._init_gpio()

    def _init_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(PIN_DI0, GPIO.OUT)
        GPIO.setup(PIN_DI1, GPIO.OUT)
        GPIO.setup(PIN_DI2_TRIGGER, GPIO.OUT)
        self.set_idle()

        mode_text = "實機 GPIO" if HAS_GPIO else "MOCK GPIO"
        print(f"\n[INFO] 啟動模式: {mode_text}")
        print("[INFO] 腳位對應: GPIO16->DI0, GPIO20->DI1, GPIO21->DI2(Trigger)")

    def _active_level(self, on: bool):
        if self.active_high:
            return GPIO.HIGH if on else GPIO.LOW
        return GPIO.LOW if on else GPIO.HIGH

    def set_idle(self):
        GPIO.output(PIN_DI0, self._active_level(False))
        GPIO.output(PIN_DI1, self._active_level(False))
        GPIO.output(PIN_DI2_TRIGGER, self._active_level(False))

    def send_code(self, code: str):
        if len(code) != 2 or any(bit not in "01" for bit in code):
            print("[ERROR] code 必須是兩位元，例如: 00, 01, 10, 11")
            return

        bit0_on = code[0] == "1"
        bit1_on = code[1] == "1"

        GPIO.output(PIN_DI0, self._active_level(bit0_on))
        GPIO.output(PIN_DI1, self._active_level(bit1_on))
        print(f"[SEND] DI0/DI1 = {code}，等待 {self.settle_ms} ms")
        time.sleep(self.settle_ms / 1000.0)

        GPIO.output(PIN_DI2_TRIGGER, self._active_level(True))
        print(f"[SEND] DI2 Trigger ON {self.pulse_ms} ms")
        time.sleep(self.pulse_ms / 1000.0)
        GPIO.output(PIN_DI2_TRIGGER, self._active_level(False))
        print("[SEND] DI2 Trigger OFF")

        time.sleep(self.hold_ms / 1000.0)
        self.set_idle()
        print("[SEND] 全部回到 Idle\n")

    def run_sequence(self, repeat=2):
        sequence = ["00", "01", "10", "11"]
        print(f"\n[TEST] 連續測試開始，共 {repeat} 輪")
        for round_idx in range(repeat):
            print(f"[TEST] 第 {round_idx + 1}/{repeat} 輪")
            for code in sequence:
                self.send_code(code)
                time.sleep(0.2)
        print("[TEST] 連續測試完成\n")

    def update_timing(self):
        try:
            settle = int(input(f"Settle ms (目前 {self.settle_ms}): ").strip())
            pulse = int(input(f"Pulse ms (目前 {self.pulse_ms}): ").strip())
            hold = int(input(f"Hold ms (目前 {self.hold_ms}): ").strip())
            self.settle_ms = max(0, settle)
            self.pulse_ms = max(10, pulse)
            self.hold_ms = max(0, hold)
            print("[INFO] 時序已更新\n")
        except ValueError:
            print("[WARN] 請輸入整數\n")

    def toggle_active_logic(self):
        self.active_high = not self.active_high
        mode = "Active-High" if self.active_high else "Active-Low"
        print(f"[INFO] 輸出邏輯切換為 {mode}\n")
        self.set_idle()


def print_menu(tester: SignalTester):
    logic = "Active-High" if tester.active_high else "Active-Low"
    print("=" * 56)
    print("機械手臂 DI0~DI2 GPIO 測試工具")
    print(f"目前邏輯: {logic}")
    print(f"目前時序: settle={tester.settle_ms}ms, pulse={tester.pulse_ms}ms, hold={tester.hold_ms}ms")
    print("1) 送單次碼 (00/01/10/11)")
    print("2) 連續測試序列 (00->01->10->11)")
    print("3) 切換 Active-High / Active-Low")
    print("4) 調整時序")
    print("q) 離開")
    print("=" * 56)


def main():
    tester = SignalTester()
    try:
        while True:
            print_menu(tester)
            choice = input("請選擇: ").strip().lower()

            if choice == "1":
                code = input("輸入 2-bit 碼 (00/01/10/11): ").strip()
                tester.send_code(code)
            elif choice == "2":
                try:
                    repeat = int(input("測試輪數 (建議 1~5): ").strip())
                except ValueError:
                    repeat = 2
                tester.run_sequence(repeat=max(1, repeat))
            elif choice == "3":
                tester.toggle_active_logic()
            elif choice == "4":
                tester.update_timing()
            elif choice == "q":
                break
            else:
                print("[WARN] 無效選項\n")
    finally:
        tester.set_idle()
        if HAS_GPIO:
            GPIO.cleanup()
        print("[INFO] 程式結束，GPIO 已清理")


if __name__ == "__main__":
    main()