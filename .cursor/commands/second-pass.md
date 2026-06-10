# second-pass

Thanks for that. Let's review the implementation and take a step back to think about our solution. Are we happy with it? Is there a simpler / more efficient solution that is better? If not, are there any low-hanging fruit or easy improvements we can further make to our solution to make it even better?

Have we covered the logic using tests? Have we added/updated all relevant docs? Have we removed any debug/temp work? Can we further simplify the implementation to make the most minimal diff possible?

Run all tests, not just the new ones, but the entire suite. Ensure there are no regressions.

ONLY once tests pass and ONLY if we are happy with our solution, propose a simple one-liner git commit message. Do not commit or push unless the user explicitly approves the message.

If you see a glaring bug or easy opportunity for improvement, suggest that and do not propose a commit until we are satisfied that our work is high quality, fulfills requirements, and doesn't break existing functionality.

This command will be available in chat with /second-pass
