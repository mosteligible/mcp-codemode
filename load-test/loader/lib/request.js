import http from 'k6/http';
import exec from 'k6/execution';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

import { buildRequestParams, buildRunUrl, getThinkTimeSeconds } from './config.js';
import { getPayloadProfile, pickMixedPayload } from './payloads.js';
import { buildSessionContext } from './session.js';

export const invalidJsonResponses = new Rate('invalid_json_responses');
export const missingOutputResponses = new Rate('missing_output_responses');
export const commandErrorResponses = new Rate('command_error_responses');

function validateResponse(payload, response, parsed, tags) {
	const responseShapeOk = check(parsed, {
		'response includes output': (body) => typeof body.output === 'string',
		'response error field is string when present': (body) => typeof body.error === 'undefined' || typeof body.error === 'string',
		'response contains expected marker': (body) => typeof body.output === 'string' && body.output.includes(payload.expectText),
	});

	missingOutputResponses.add(typeof parsed.output !== 'string', tags);
	commandErrorResponses.add(typeof parsed.error === 'string' && parsed.error.trim() !== '', tags);

	return responseShapeOk;
}


export function runPayload(payload, extraTags = {}, sessionOptions = {}) {
	const sessionContext = buildSessionContext({
		suite: extraTags.suite,
		...sessionOptions,
	});
	const tags = {
		endpoint: 'run',
		workload: payload.name,
		language: payload.language,
		session_mode: sessionContext.mode,
		...extraTags,
	};

	const requestBody = {
		code: payload.code,
		language: payload.language,
	};
	if (sessionContext.sessionId !== '') {
		requestBody.sessionId = sessionContext.sessionId;
	}

	const response = http.post(
		buildRunUrl(),
		JSON.stringify(requestBody),
		buildRequestParams(tags),
	);

	let parsed = null;
	let parsedOk = true;
	try {
		parsed = response.json();
	} catch (_error) {
		parsedOk = false;
	}

	invalidJsonResponses.add(!parsedOk, tags);

	const transportOk = check(response, {
		'status is 200': (res) => res.status === 200,
		'response is json': () => parsedOk,
	});

	const applicationOk = parsedOk ? validateResponse(payload, response, parsed, tags) : false;
	const thinkTimeSeconds = getThinkTimeSeconds();
	if (thinkTimeSeconds > 0) {
		sleep(thinkTimeSeconds);
	}

	return {
		response,
		parsed,
		ok: transportOk && applicationOk,
	};
}

export function runNamedPayload(name, extraTags = {}) {
	return runPayload(getPayloadProfile(name), extraTags, { strategy: 'vu' });
}

export function runMixedPayload(extraTags = {}) {
	return runPayload(pickMixedPayload(exec.scenario.iterationInTest), extraTags, { strategy: 'pool' });
}