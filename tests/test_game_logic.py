from logic_utils import check_guess

def test_winning_guess():
    # If the secret is 50 and guess is 50, it should be a win
    outcome, _ = check_guess(50, 50)
    assert outcome == "Win"

def test_guess_too_high():
    # If secret is 50 and guess is 60, hint should be "Too High"
    outcome, _ = check_guess(60, 50)
    assert outcome == "Too High"

def test_guess_too_low():
    # If secret is 50 and guess is 40, hint should be "Too Low"
    outcome, _ = check_guess(40, 50)
    assert outcome == "Too Low"


# Bug fix 1: outcome labels were swapped
# guess < secret was returning "Too High" instead of "Too Low" and vice versa
def test_low_guess_outcome_label_is_too_low():
    outcome, _ = check_guess(10, 50)
    assert outcome == "Too Low"

def test_high_guess_outcome_label_is_too_high():
    outcome, _ = check_guess(90, 50)
    assert outcome == "Too High"


# Bug fix 2: difficulty ranges — Normal was smaller than Hard (switched)
from logic_utils import get_range_for_difficulty

def test_normal_range_wider_than_easy():
    _, easy_high = get_range_for_difficulty("Easy")
    _, normal_high = get_range_for_difficulty("Normal")
    assert normal_high > easy_high

def test_hard_range_wider_than_normal():
    _, normal_high = get_range_for_difficulty("Normal")
    _, hard_high = get_range_for_difficulty("Hard")
    assert hard_high > normal_high


# Bug fix 3: attempts initialized to 1 instead of 0, inconsistent with new game reset
# This is Streamlit session state and not unit-testable via logic_utils.
# Covered by manual/integration testing.
