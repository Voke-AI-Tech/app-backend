from pipelines.live_conversation import live_conversation_pipeline

# Companion evaluation is identical to Live — the only difference between the two
# modes is how Gemini is prompted (role-aware vs generic). The audio evaluation
# pipeline is the same, so we simply re-export it under the companion name.
companion_conversation_pipeline = live_conversation_pipeline
