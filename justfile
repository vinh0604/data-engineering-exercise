aider:
	DEEPSEEK_API_KEY=$(cat .deepseek_key) aider --deepseek

aider-architect:
	OPENAI_API_KEY=$(cat .openai_key) aider --o1-preview --architect