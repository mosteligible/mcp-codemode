import exec from 'k6/execution';

import { getSessionMode, getSessionPoolSize, getSessionPrefix, includeSessionIdInPayload } from './config.js';

function sanitizeSuiteName(suite) {
	return String(suite || 'default').replace(/[^a-zA-Z0-9_-]/g, '-');
}

function buildPoolSessionId(prefix, suite, poolSize) {
	const slot = exec.scenario.iterationInTest % poolSize;
	return `${prefix}-${suite}-session-${slot}`;
}

function buildVuSessionId(prefix, suite) {
	return `${prefix}-${suite}-vu-${exec.vu.idInTest}`;
}

function buildIterationSessionId(prefix, suite) {
	return `${prefix}-${suite}-iter-${exec.scenario.iterationInTest}`;
}

export function buildSessionContext(options = {}) {
	const suite = sanitizeSuiteName(options.suite);
	if (!includeSessionIdInPayload()) {
		return {
			sessionId: '',
			mode: 'disabled',
		};
	}

	const prefix = getSessionPrefix();
	const configuredMode = options.strategy || getSessionMode();

	switch (configuredMode) {
	case 'vu':
		return {
			sessionId: buildVuSessionId(prefix, suite),
			mode: 'vu',
		};
	case 'iteration':
		return {
			sessionId: buildIterationSessionId(prefix, suite),
			mode: 'iteration',
		};
	case 'pool':
		return {
			sessionId: buildPoolSessionId(prefix, suite, getSessionPoolSize()),
			mode: 'pool',
		};
	default:
		throw new Error(`unsupported session mode: ${configuredMode}`);
	}
}