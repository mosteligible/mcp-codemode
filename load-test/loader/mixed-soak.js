import { buildConstantArrivalRateScenario, getCommonThresholds } from './lib/config.js';
import { runMixedPayload } from './lib/request.js';

export const options = {
	thresholds: {
		...getCommonThresholds(),
		command_error_responses: ['rate<0.05'],
	},
	scenarios: {
		mixed_soak: buildConstantArrivalRateScenario('SOAK', {
			rate: 8,
			timeUnit: '1s',
			duration: '20m',
			preAllocatedVUs: 8,
			maxVUs: 64,
		}),
	},
};

export default function() {
	runMixedPayload({ suite: 'mixed-soak' });
}