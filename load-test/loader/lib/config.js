const DEFAULT_BASE_URL = 'http://localhost:8080';
const DEFAULT_RUN_PATH = '/run';
const DEFAULT_REQUEST_TIMEOUT = '35s';

function stringFromEnv(name, fallback) {
	const value = __ENV[name];
	if (typeof value !== 'string') {
		return fallback;
	}

	const trimmed = value.trim();
	return trimmed === '' ? fallback : trimmed;
}

function numberFromEnv(name, fallback) {
	const parsed = Number.parseFloat(__ENV[name] ?? '');
	return Number.isFinite(parsed) ? parsed : fallback;
}

function integerFromEnv(name, fallback) {
	const parsed = Number.parseInt(__ENV[name] ?? '', 10);
	return Number.isFinite(parsed) ? parsed : fallback;
}

export function getBaseUrl() {
	return stringFromEnv('CODERUNNER_BASE_URL', DEFAULT_BASE_URL);
}

export function getRunPath() {
	return stringFromEnv('CODERUNNER_RUN_PATH', DEFAULT_RUN_PATH);
}

export function buildRunUrl() {
	return `${getBaseUrl().replace(/\/$/, '')}${getRunPath()}`;
}

export function getRequestTimeout() {
	return stringFromEnv('CODERUNNER_REQUEST_TIMEOUT', DEFAULT_REQUEST_TIMEOUT);
}

export function getThinkTimeSeconds() {
	return numberFromEnv('THINK_TIME_SECONDS', 0);
}

export function buildRequestParams(tags = {}) {
	return {
		headers: {
			'Content-Type': 'application/json',
		},
		timeout: getRequestTimeout(),
		tags,
	};
}

export function buildRampingArrivalRateScenario(prefix, defaults) {
	return {
		executor: 'ramping-arrival-rate',
		startRate: integerFromEnv(`${prefix}_START_RATE`, defaults.startRate),
		preAllocatedVUs: integerFromEnv(`${prefix}_PRE_ALLOCATED_VUS`, defaults.preAllocatedVUs),
		maxVUs: integerFromEnv(`${prefix}_MAX_VUS`, defaults.maxVUs),
		timeUnit: stringFromEnv(`${prefix}_TIME_UNIT`, defaults.timeUnit),
		stages: defaults.stages.map((stage, index) => ({
			target: integerFromEnv(`${prefix}_STAGE_${index + 1}_TARGET`, stage.target),
			duration: stringFromEnv(`${prefix}_STAGE_${index + 1}_DURATION`, stage.duration),
		})),
	};
}

export function buildConstantArrivalRateScenario(prefix, defaults) {
	return {
		executor: 'constant-arrival-rate',
		rate: integerFromEnv(`${prefix}_RATE`, defaults.rate),
		timeUnit: stringFromEnv(`${prefix}_TIME_UNIT`, defaults.timeUnit),
		duration: stringFromEnv(`${prefix}_DURATION`, defaults.duration),
		preAllocatedVUs: integerFromEnv(`${prefix}_PRE_ALLOCATED_VUS`, defaults.preAllocatedVUs),
		maxVUs: integerFromEnv(`${prefix}_MAX_VUS`, defaults.maxVUs),
	};
}

export function buildConstantVusScenario(prefix, defaults) {
	return {
		executor: 'constant-vus',
		vus: integerFromEnv(`${prefix}_VUS`, defaults.vus),
		duration: stringFromEnv(`${prefix}_DURATION`, defaults.duration),
	};
}

export function getCommonThresholds() {
	return {
		http_req_failed: ['rate<0.01'],
		http_req_duration: ['p(95)<30000', 'p(99)<35000'],
		invalid_json_responses: ['rate==0'],
		missing_output_responses: ['rate==0'],
	};
}