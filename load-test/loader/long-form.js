import exec from 'k6/execution';

import { buildConstantVusScenario, getCommonThresholds } from './lib/config.js';
import { buildBoundedLongPayload } from './lib/payloads.js';
import { runPayload } from './lib/request.js';

export const options = {
	thresholds: {
		...getCommonThresholds(),
		command_error_responses: ['rate==0'],
	},
	scenarios: {
		long_form: buildConstantVusScenario('LONG_FORM', {
			vus: 8,
			duration: '5m',
		}),
	},
};

export default function() {
	const payload = buildBoundedLongPayload(exec.scenario.iterationInTest);
	runPayload(payload, {
		suite: 'long-form',
		duration_seconds: String(payload.durationSeconds),
	});
}