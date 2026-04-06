function integerFromEnv(name, fallback) {
	const parsed = Number.parseInt(__ENV[name] ?? '', 10);
	return Number.isFinite(parsed) ? parsed : fallback;
}

function shortCommand() {
	return "printf 'short-ok\\n'";
}

function mediumCommand() {
	const iterations = integerFromEnv('MEDIUM_PYTHON_ITERATIONS', 4000000);
	return [
		"python - <<'PY'",
		'import math',
		'acc = 0.0',
		`for i in range(${iterations}):`,
		'    acc += math.sqrt(i % 1000)',
		"print(f'medium-ok:{acc:.2f}')",
		'PY',
	].join('\n');
}

function longCommand() {
	const seconds = integerFromEnv('LONG_BUSY_SECONDS', 25);
	return [
		"python - <<'PY'",
		'import time',
		'start = time.time()',
		`while time.time() - start < ${seconds}:`,
		'    pass',
		"print('long-ok')",
		'PY',
	].join('\n');
}

export const payloadProfiles = {
	short: {
		name: 'short',
		language: 'bash',
		code: shortCommand(),
		expectText: 'short-ok',
	},
	medium: {
		name: 'medium',
		language: 'bash',
		code: mediumCommand(),
		expectText: 'medium-ok:',
	},
	long: {
		name: 'long',
		language: 'bash',
		code: longCommand(),
		expectText: 'long-ok',
	},
};

function buildWeightedMix() {
	const shortWeight = integerFromEnv('MIX_SHORT_WEIGHT', 70);
	const mediumWeight = integerFromEnv('MIX_MEDIUM_WEIGHT', 20);
	const longWeight = integerFromEnv('MIX_LONG_WEIGHT', 10);
	const mix = [];

	for (let index = 0; index < shortWeight; index += 1) {
		mix.push(payloadProfiles.short);
	}
	for (let index = 0; index < mediumWeight; index += 1) {
		mix.push(payloadProfiles.medium);
	}
	for (let index = 0; index < longWeight; index += 1) {
		mix.push(payloadProfiles.long);
	}

	if (mix.length === 0) {
		return [payloadProfiles.short];
	}

	return mix;
}

export function getPayloadProfile(name) {
	const payload = payloadProfiles[name];
	if (!payload) {
		throw new Error(`unknown payload profile: ${name}`);
	}
	return payload;
}

export function pickMixedPayload(iterationInTest) {
	const mix = buildWeightedMix();
	return mix[iterationInTest % mix.length];
}