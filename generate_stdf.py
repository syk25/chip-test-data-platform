#!/usr/bin/env python3
"""
STDF v4 데모 파일 생성기.
외부 패키지 불필요 — Python 표준 라이브러리만 사용.

사용법:
    python3 generate_stdf.py
    python3 generate_stdf.py --wafers 5 --parts 20 --fail-rate 0.2
"""
import argparse
import random
import struct
import time
from pathlib import Path


# ─── STDF 바이너리 직렬화 헬퍼 ─────────────────────────────────────────────

def _cn(s: str) -> bytes:
    """Cn 타입: 1바이트 길이 + ASCII 문자열"""
    if not s:
        return b'\x00'
    b = s.encode('ascii')
    return bytes([len(b)]) + b


def _rec(typ: int, sub: int, data: bytes) -> bytes:
    """STDF 레코드 = 4바이트 헤더(len, typ, sub) + 데이터"""
    return struct.pack('<HBB', len(data), typ, sub) + data


# ─── 레코드 생성 함수 ────────────────────────────────────────────────────────

def far() -> bytes:
    """File Attributes Record — 파일 첫 레코드 (필수)"""
    return _rec(0, 10, struct.pack('BB', 2, 4))  # CPU_TYPE=2(LE), STDF_VER=4


def mir(lot_id: str, part_typ: str, start_t: int) -> bytes:
    """Master Information Record — Lot 정보"""
    d = struct.pack('<II', start_t, start_t)  # SETUP_T, START_T
    d += struct.pack('B', 1)    # STAT_NUM
    d += b' ' * 3               # MODE_COD, RTST_COD, PROT_COD
    d += struct.pack('<H', 0)   # BURN_TIM
    d += b' '                   # CMOD_COD
    d += _cn(lot_id)            # LOT_ID
    d += _cn(part_typ)          # PART_TYP
    d += _cn('TESTER-NODE-01')  # NODE_NAM
    d += _cn('ATE-X1000')       # TSTR_TYP
    return _rec(1, 10, d)


def wir(wafer_id: str, head_num: int, start_t: int) -> bytes:
    """Wafer Information Record — Wafer 시작"""
    d = struct.pack('BB', head_num, 255)  # HEAD_NUM, SITE_GRP
    d += struct.pack('<I', start_t)        # START_T
    d += _cn(wafer_id)                     # WAFER_ID
    return _rec(2, 10, d)


def pir() -> bytes:
    """Part Information Record — Part 검사 시작"""
    return _rec(5, 10, struct.pack('BB', 1, 1))  # HEAD_NUM, SITE_NUM


def ptr(test_num: int, name: str, result: float, unit: str,
        lo: float, hi: float, is_pass: bool) -> bytes:
    """Parametric Test Record — 측정값 1건"""
    test_flg = 0x00 if is_pass else 0x80  # bit7=1 → FAIL
    d = struct.pack('<I', test_num)  # TEST_NUM (U4)
    d += struct.pack('BB', 1, 1)     # HEAD_NUM, SITE_NUM
    d += struct.pack('BB', test_flg, 0x00)  # TEST_FLG, PARM_FLG
    d += struct.pack('<f', result)   # RESULT (R4)
    d += _cn(name)                   # TEST_TXT
    d += _cn('')                     # ALARM_ID
    d += struct.pack('B', 0x00)      # OPT_FLAG (모든 선택 필드 유효)
    d += struct.pack('bbb', 0, 0, 0) # RES_SCAL, LLM_SCAL, HLM_SCAL
    d += struct.pack('<ff', lo, hi)  # LO_LIMIT, HI_LIMIT
    d += _cn(unit)                   # UNITS
    return _rec(15, 10, d)


def prr(part_id: str, hard_bin: int, soft_bin: int,
        is_pass: bool, num_test: int, x: int, y: int) -> bytes:
    """Part Results Record — Part 검사 종료"""
    part_flg = 0x00 if is_pass else 0x08  # bit3=1 → FAIL
    d = struct.pack('BB', 1, 1)                  # HEAD_NUM, SITE_NUM
    d += struct.pack('B', part_flg)              # PART_FLG
    d += struct.pack('<H', num_test)             # NUM_TEST
    d += struct.pack('<HH', hard_bin, soft_bin)  # HARD_BIN, SOFT_BIN
    d += struct.pack('<hh', x, y)                # X_COORD, Y_COORD
    d += struct.pack('<I', 150)                  # TEST_T (150ms)
    d += _cn(part_id)                            # PART_ID
    return _rec(5, 20, d)


def wrr(wafer_id: str, head_num: int, finish_t: int, part_cnt: int) -> bytes:
    """Wafer Results Record — Wafer 종료"""
    d = struct.pack('BB', head_num, 255)  # HEAD_NUM, SITE_GRP
    d += struct.pack('<I', finish_t)       # FINISH_T
    d += struct.pack('<I', part_cnt)       # PART_CNT
    d += struct.pack('<IIII',              # RTST_CNT, ABRT_CNT, GOOD_CNT, FUNC_CNT
                     0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF)
    d += _cn(wafer_id)                     # WAFER_ID
    return _rec(2, 20, d)


def mrr(finish_t: int) -> bytes:
    """Master Results Record — 파일 종료"""
    d = struct.pack('<I', finish_t)  # FINISH_T
    d += b' '                        # DISP_COD
    d += _cn('') + _cn('')           # USR_DESC, EXC_DESC
    return _rec(1, 20, d)


# ─── 메인 ────────────────────────────────────────────────────────────────────

TESTS = [
    # (test_num, name, unit, lo_limit, hi_limit, nominal, sigma)
    (1000, 'VCC_VOLTAGE',  'V',   1.70, 1.90, 1.80, 0.02),
    (2000, 'IDDQ_CURRENT', 'mA',  0.00, 5.00, 2.50, 0.50),
    (3000, 'FREQ_OSC',     'MHz', 95.0, 105.0, 100.0, 1.0),
    (4000, 'LEAKAGE_CURR', 'uA',  0.00, 1.00, 0.30, 0.10),
    (5000, 'OUTPUT_VOLT',  'V',   2.90, 3.10, 3.00, 0.03),
]


def generate(lot_id: str, part_typ: str, wafer_ids: list[str],
             parts_per_wafer: int, fail_rate: float, seed: int) -> bytes:
    random.seed(seed)
    now = int(time.time())
    out = bytearray()

    out += far()
    out += mir(lot_id, part_typ, now)

    for w_idx, wafer_id in enumerate(wafer_ids):
        wafer_start = now + w_idx * 3600
        out += wir(wafer_id, head_num=1, start_t=wafer_start)

        for p_idx in range(parts_per_wafer):
            part_id = f'{wafer_id}-P{p_idx+1:02d}'
            x, y = p_idx % 5, p_idx // 5

            out += pir()

            # 불량 Part는 VCC_VOLTAGE 범위 초과
            is_part_fail = random.random() < fail_rate
            part_pass = True
            for test_num, name, unit, lo, hi, nom, sigma in TESTS:
                if is_part_fail and test_num == 1000:
                    result = random.gauss(hi + 0.05, sigma * 0.5)
                    t_pass = False
                else:
                    result = random.gauss(nom, sigma)
                    t_pass = lo <= result <= hi
                if not t_pass:
                    part_pass = False
                out += ptr(test_num, name, result, unit, lo, hi, t_pass)

            hard_bin = 1 if part_pass else 2
            soft_bin = 1 if part_pass else 200
            out += prr(part_id, hard_bin, soft_bin, part_pass, len(TESTS), x, y)

        out += wrr(wafer_id, head_num=1,
                   finish_t=wafer_start + 1800,
                   part_cnt=parts_per_wafer)

    out += mrr(finish_t=now + len(wafer_ids) * 3600)
    return bytes(out)


def main():
    parser = argparse.ArgumentParser(description='STDF v4 데모 파일 생성기')
    parser.add_argument('--lot-id',    default='LOT-DEMO-001')
    parser.add_argument('--part-typ',  default='CHIP-QS-100A')
    parser.add_argument('--wafers',    type=int, default=3)
    parser.add_argument('--parts',     type=int, default=10)
    parser.add_argument('--fail-rate', type=float, default=0.15)
    parser.add_argument('--seed',      type=int, default=42)
    parser.add_argument('--output',    default='demo.stdf')
    args = parser.parse_args()

    wafer_ids = [f'W{i+1:02d}' for i in range(args.wafers)]
    data = generate(
        lot_id=args.lot_id,
        part_typ=args.part_typ,
        wafer_ids=wafer_ids,
        parts_per_wafer=args.parts,
        fail_rate=args.fail_rate,
        seed=args.seed,
    )

    Path(args.output).write_bytes(data)
    total_parts = args.wafers * args.parts

    print(f'생성 완료: {args.output} ({len(data):,} bytes)')
    print(f'  Lot ID : {args.lot_id}')
    print(f'  제품   : {args.part_typ}')
    print(f'  Wafer  : {args.wafers}장 ({", ".join(wafer_ids)})')
    print(f'  Part   : 총 {total_parts}개 (Wafer당 {args.parts}개)')
    print(f'  Test   : {len(TESTS)}종')
    print(f'  FAIL률 : ~{args.fail_rate*100:.0f}%')


if __name__ == '__main__':
    main()
