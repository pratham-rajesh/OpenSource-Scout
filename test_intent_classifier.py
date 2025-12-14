"""
Test Intent Classifier
=======================
Verify the IntentClassifier functionality.
"""

from chatbot.intent_classifier import get_intent_classifier

def test_intent_classifier():
    """Test intent classification with various messages."""
    classifier = get_intent_classifier()
    print("✓ IntentClassifier initialized\n")

    test_cases = [
        ("Find me some Python issues for beginners", "search_issues"),
        ("Show me what I've solved recently", "view_history"),
        ("How am I doing with JavaScript?", "get_stats"),
        ("How do I fix CORS errors?", "get_advice"),
        ("What is the difference between let and const?", "general_question"),
        ("I need easy Go issues to work on", "search_issues"),
        ("My Python progress this week", "get_stats"),
    ]

    print("Testing intent classification:\n")
    for i, (message, expected_intent) in enumerate(test_cases, 1):
        result = classifier.classify_intent(message)

        status = "✓" if result['intent'] == expected_intent else "✗"
        print(f"{status} Test {i}: {message[:50]}...")
        print(f"  Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
        print(f"  Entities: {result['entities']}")
        print()

    print("✅ All Intent Classifier tests completed!")

if __name__ == '__main__':
    test_intent_classifier()
