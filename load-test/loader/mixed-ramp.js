import { buildRampingArrivalRateScenario, getCommonThresholds } from './lib/config.js';
import { runMixedPayload } from './lib/request.js';

export const options = {
	thresholds: {
		...getCommonThresholds(),
		command_error_responses: ['rate<0.05'],
	},
	scenarios: {
		mixed_ramp: buildRampingArrivalRateScenario('RAMP', {
			startRate: 1,
			preAllocatedVUs: 4,
			maxVUs: 40,
			timeUnit: '1s',
			stages: [
				{ target: 2, duration: '2m' },
				{ target: 4, duration: '2m' },
				{ target: 8, duration: '2m' },
				{ target: 12, duration: '2m' },
				{ target: 16, duration: '2m' },
				{ target: 24, duration: '2m' },
			],
		}),
	},
};

export default function() {
	runMixedPayload({ suite: 'mixed-ramp' });
}