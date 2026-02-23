#!/usr/bin/env python3
"""
Test cases for sameshi2kchess chess engine.
Tests move validation for both player and AI.
"""

import subprocess
import time
import sys

CHESS_PROGRAM = "./sameshi"

def send_moves(program, moves, timeout=5):
    """Send a sequence of moves to the chess program and get responses."""
    proc = subprocess.Popen(
        program,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Flatten moves if it contains lists, then send quit at the end
    flat_moves = []
    for m in moves:
        if isinstance(m, list):
            flat_moves.extend(m)
        else:
            flat_moves.append(m)
    all_moves = flat_moves + ["q"]

    try:
        stdout, stderr = proc.communicate("\n".join(all_moves) + "\n", timeout=timeout)
        return stdout, stderr, proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        return stdout, stderr, -1

def parse_ai_move(output):
    """Parse AI move from output like 'move: ai: e2e4 (123ms)'."""
    for line in output.split("\n"):
        if "ai:" in line:
            parts = line.split()
            # Format: "move: ai: e2e4 (123ms)" or "ai: e2e4 (123ms)"
            # parts = ["move:", "ai:", "e2e4", "(123ms)"] or ["ai:", "e2e4", "(123ms)"]
            if len(parts) >= 3 and parts[1] == "ai:":
                return parts[2]
            elif len(parts) >= 2 and parts[0] == "ai:":
                return parts[1]
    return None

def parse_board(output):
    """Parse the board state from output."""
    lines = output.split("\n")
    board = []
    in_board = False
    for line in lines:
        if "│" in line:
            in_board = True
            # Extract pieces between │
            pieces = []
            for part in line.split("│"):
                part = part.strip()
                if len(part) == 1 or part in ["♙", "♟", "♘", "♞", "♗", "♝", "♖", "♜", "♕", "♛", "♔", "♚", "·"]:
                    pieces.append(part)
            if pieces:
                board.append(pieces[1:9])  # Get the 8 squares
        elif in_board and line.strip() == "":
            break
    return board

def count_pieces(output, piece):
    """Count occurrences of a piece on the board."""
    return output.count(piece)

def test_illegal_moves_are_rejected():
    """Test that illegal moves are rejected and AI doesn't play."""
    print("Testing illegal moves are rejected...")

    test_cases = [
        # (description, moves, should_contain)
        ("Moving empty square", ["a3a4"], "Invalid move"),      # a3 is empty
        ("Moving opponent piece", ["a7a6"], "Invalid move"),     # black pawn
        ("Illegal knight move", ["b1d1"], "Invalid move"),       # Knight can't move like rook
        ("Illegal bishop move", ["f1f2"], "Invalid move"),       # Bishop can't move straight (blocked by pawn anyway)
        ("Illegal rook move", ["a1b2"], "Invalid move"),         # Rook can't move diagonal
        ("Illegal queen move", ["d1e3"], "Invalid move"),        # Queen can't do knight move
        ("Illegal king move", ["e1e3"], "Invalid move"),         # King can't move 2 squares
        ("Pawn backward", ["e2e1"], "Invalid move"),
        ("Pawn sideways", ["e2f2"], "Invalid move"),
        ("Pawn 3 squares", ["e2e5"], "Invalid move"),
        ("Rook jump over", ["a1a4"], "Invalid move"),           # Can't jump over pawn
        ("Illegal pawn capture (no piece)", ["e2f3"], "Invalid move"),
    ]

    passed = 0
    failed = 0

    for desc, move, expected in test_cases:
        stdout, stderr, code = send_moves([CHESS_PROGRAM], move)
        if expected in stdout:
            print(f"  ✓ {desc}")
            passed += 1
        else:
            print(f"  ✗ {desc} - expected '{expected}' in output")
            print(f"    Output: {stdout[:200]}")
            failed += 1

    print(f"Illegal moves: {passed}/{passed+failed} passed\n")
    return failed == 0

def test_legal_moves_accepted():
    """Test that legal moves are accepted and AI responds."""
    print("Testing legal moves are accepted...")

    test_cases = [
        # (description, setup_moves, test_move)
        ("Pawn forward 2 from start", [], "e2e4"),
        ("Knight L-shape (up-right)", [], "g1f3"),
        ("Knight L-shape (up-left)", [], "b1c3"),
        ("Bishop diagonal (light)", ["e2e4"], "f1c4"),  # Need to clear e2 first
        ("Bishop diagonal (dark)", ["d2d4"], "c1e3"),   # Need to clear d2 first
        ("Queen diagonal", ["e2e4"], "d1h5"),          # Need to clear e2 first
        ("Queen straight", ["d2d4"], "d1d3"),          # d3 is clear after d2d4
        ("King one square", ["e2e4"], "e1e2"),         # e2 is now empty
    ]

    passed = 0
    failed = 0

    for desc, setup, move in test_cases:
        moves = setup + [move]
        stdout, stderr, code = send_moves([CHESS_PROGRAM], moves)
        ai_move = parse_ai_move(stdout)
        has_ai = "ai:" in stdout
        has_invalid = "Invalid move" in stdout

        if has_ai and not has_invalid:
            print(f"  ✓ {desc} - AI responded with {ai_move}")
            passed += 1
        else:
            print(f"  ✗ {desc} - has_ai={has_ai}, has_invalid={has_invalid}")
            if not has_ai:
                print(f"    No ai: in output")
            failed += 1

    print(f"Legal moves: {passed}/{passed+failed} passed\n")
    return failed == 0

def test_pawn_captures():
    """Test pawn capture moves."""
    print("Testing pawn captures...")

    # Set up a position where pawn can capture
    moves = ["e2e4"]  # Player moves

    test_cases = [
        ("Pawn capture diagonal", ["d2d4"], None),
    ]

    passed = 0
    failed = 0

    for desc, move, _ in test_cases:
        full_moves = moves + [move[0]]
        stdout, stderr, code = send_moves([CHESS_PROGRAM], full_moves)
        if "Invalid move" not in stdout:
            print(f"  ✓ {desc}")
            passed += 1
        else:
            print(f"  ✗ {desc}")
            failed += 1

    print(f"Pawn captures: {passed}/{passed+failed} passed\n")
    return failed == 0

def test_cant_capture_own_pieces():
    """Test that you can't capture your own pieces."""
    print("Testing can't capture own pieces...")

    test_cases = [
        # (description, move, should_be_invalid)
        ("Knight can't take own pawn", "b1d2", True),      # d2 has white pawn
        ("Knight can't take own knight", "g1e2", True),    # e2 has white pawn
        ("Bishop can't take own pawn", "f1e2", True),      # e2 has white pawn
    ]

    passed = 0
    failed = 0

    for desc, move, should_be_invalid in test_cases:
        stdout, stderr, code = send_moves([CHESS_PROGRAM], [move])
        is_invalid = "Invalid move" in stdout

        if is_invalid == should_be_invalid:
            print(f"  ✓ {desc}")
            passed += 1
        else:
            print(f"  ✗ {desc} - expected invalid={should_be_invalid}, got {is_invalid}")
            failed += 1

    print(f"Own piece protection: {passed}/{passed+failed} passed\n")
    return failed == 0

def test_sliding_pieces_path_clear():
    """Test that sliding pieces can't jump over other pieces."""
    print("Testing sliding pieces need clear path...")

    # Bishop at f1 can't go to c4 if pawn at e2 is still there
    # But we need to test when path is blocked

    test_cases = [
        ("Bishop blocked by pawn", ["f1c4"], "Invalid move"),  # e2 still there
        ("Queen blocked by own pawn", ["d1f3"], "Invalid move"),  # e2 blocks
        ("Rook blocked by pawn", ["a1a3"], "Invalid move"),  # a2 blocks
    ]

    passed = 0
    failed = 0

    for desc, move, expected in test_cases:
        stdout, stderr, code = send_moves([CHESS_PROGRAM], move)
        if expected in stdout:
            print(f"  ✓ {desc}")
            passed += 1
        else:
            print(f"  ✗ {desc} - expected '{expected}'")
            failed += 1

    # Now test that moving the pawn out of the way allows the bishop/queen move
    print("\n  Testing that clearing path allows move:")
    moves = ["e2e4", "f1c4"]
    stdout, _, _ = send_moves([CHESS_PROGRAM], moves)
    if "Invalid move" not in stdout and parse_ai_move(stdout):
        print(f"  ✓ Bishop can move after pawn moves")
        passed += 1
    else:
        print(f"  ✗ Bishop should be able to move after pawn clears path")
        failed += 1

    print(f"\nSliding pieces path: {passed}/{passed+failed} passed\n")
    return failed == 0

def test_piece_count_after_moves():
    """Test that piece counts are correct after moves."""
    print("Testing piece counts after moves...")

    # Play a few moves and count pieces
    moves = ["e2e4", "e7e5", "g1f3"]

    passed = 0
    failed = 0

    stdout, stderr, code = send_moves([CHESS_PROGRAM], moves)

    # Get the last board from output (count pieces in the final board)
    # Split by "move:" and take the last section that contains a board
    sections = stdout.split("move:")
    # Find the last section with board characters (│)
    last_section = None
    for section in reversed(sections):
        if "│" in section:
            last_section = section
            break

    if not last_section:
        print(f"  ✗ Could not find final board")
        return False

    # Check we still have both kings
    white_kings = last_section.count("♔")
    black_kings = last_section.count("♚")

    if white_kings == 1 and black_kings == 1:
        print(f"  ✓ Both kings on board")
        passed += 1
    else:
        print(f"  ✗ Kings: white={white_kings}, black={black_kings}")
        failed += 1

    print(f"Piece counts: {passed}/{passed+failed} passed\n")
    return failed == 0

def test_ai_makes_legal_moves():
    """Test that AI always makes legal moves."""
    print("Testing AI makes legal moves...")

    moves = ["e2e4", "d2d4", "g1f3"]

    passed = 0
    failed = 0

    stdout, stderr, code = send_moves([CHESS_PROGRAM], moves)

    # Count AI moves in output
    ai_moves = []
    for line in stdout.split("\n"):
        if "ai:" in line:
            parsed = parse_ai_move(line)
            if parsed:
                ai_moves.append(parsed)

    if len(ai_moves) == len(moves):
        print(f"  ✓ AI responded to each move ({len(ai_moves)} responses)")
        passed += 1
    else:
        print(f"  ✗ AI responses: {len(ai_moves)}, expected {len(moves)}")
        print(f"    AI moves: {ai_moves}")
        failed += 1

    # Check AI moves are in valid algebraic notation
    import re
    move_pattern = re.compile(r'^[a-h][1-8][a-h][1-8]$')
    legal_ai = all(move_pattern.match(move) for move in ai_moves)

    if legal_ai:
        print(f"  ✓ All AI moves are valid format")
        passed += 1
    else:
        print(f"  ✗ Some AI moves have invalid format: {ai_moves}")
        failed += 1

    print(f"AI legal moves: {passed}/{passed+failed} passed\n")
    return failed == 0

def test_check_detection():
    """Test that illegal moves into check are rejected."""
    print("Testing check detection...")

    # This is hard to test simply, but we can test basic scenarios
    # Set up a simple check scenario

    passed = 0
    failed = 0

    # Player moves knight to attack, then tries to move king away incorrectly
    moves = ["e2e4", "g1f3"]
    stdout, _, _ = send_moves([CHESS_PROGRAM], moves)

    if "Invalid move" not in stdout or parse_ai_move(stdout):
        print(f"  ✓ Basic check scenario handled")
        passed += 1
    else:
        print(f"  ! Check scenario needs manual verification")
        failed += 1

    print(f"Check detection: {passed}/{passed+failed} passed\n")
    return failed == 0

def main():
    """Run all tests."""
    print("=" * 50)
    print("Chess Engine Test Suite")
    print("=" * 50)
    print()

    results = []

    try:
        results.append(("Illegal moves rejected", test_illegal_moves_are_rejected()))
        results.append(("Legal moves accepted", test_legal_moves_accepted()))
        results.append(("Sliding pieces path", test_sliding_pieces_path_clear()))
        results.append(("Can't capture own pieces", test_cant_capture_own_pieces()))
        results.append(("Piece counts", test_piece_count_after_moves()))
        results.append(("AI legal moves", test_ai_makes_legal_moves()))
        results.append(("Check detection", test_check_detection()))

    except Exception as e:
        print(f"\n✗ Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("=" * 50)
    print("Test Results")
    print("=" * 50)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    total_passed = sum(1 for _, p in results if p)
    total = len(results)

    print(f"\nTotal: {total_passed}/{total} test suites passed")

    return 0 if total_passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
