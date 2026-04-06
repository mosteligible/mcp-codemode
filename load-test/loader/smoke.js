import { buildConstantVusScenario, getCommonThresholds } from './lib/config.js';
import { runNamedPayload } from './lib/request.js';

export const options = {
	thresholds: {
		...getCommonThresholds(),
		command_error_responses: ['rate==0'],
	},
	scenarios: {
		smoke: buildConstantVusScenario('SMOKE', {
			vus: 1,
			duration: '30s',
		}),
	},
};

export default function() {
	runNamedPayload('short', { suite: 'smoke' });
}