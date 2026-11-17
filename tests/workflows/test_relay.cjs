// Node's built-in test runner; exercises the exact exported relay code.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const workflow = JSON.parse(fs.readFileSync(path.join(__dirname, '../../workflows/festtrackai.json')));
const nodes = Object.fromEntries(workflow.nodes.map(n => [n.name, n]));
const relay = new Function('$input', nodes['Relay HTML'].parameters.jsCode);
const html = '<html><script type="application/ld+json">{"@type":"ItemList","itemListElement":[{"item":{"name":"Relay Fest"}}]}</script></html>';

test('raw HTML stays byte-for-byte intact through each supported envelope', () => {
  for (const json of [{body: html}, {data: html}, {html}, {data: {body: html}}, {data: {html}}]) {
    const items = relay({all: () => [{json}]});
    assert.equal(items[0].json.html, html);
    const expression = nodes.Send.parameters.body;
    assert.ok(expression.startsWith('={{'));
    const send = new Function('$json', 'return (' + expression.slice(3, -2) + ')');
    assert.equal(send(items[0].json), html);
  }
});

test('invalid responses stop before Send rather than posting an empty body', () => {
  for (const json of [{}, {data: {name: 'Parsed JSON'}}, {body: 'plain text'}, {body: null}]) {
    assert.throws(() => relay({all: () => [{json}]}), /did not return raw HTML/);
  }
});

test('items remain paired and no festival parsing happens in the relay', () => {
  const items = relay({all: () => [{json: {body: html}}, {json: {data: html}}]});
  assert.deepEqual(items.map(item => item.pairedItem.item), [0, 1]);
  assert.deepEqual(items.map(item => Object.keys(item.json)), [['html'], ['html']]);
});

test('workflow is a scrape-and-forward relay without user credentials', () => {
  assert.deepEqual(Object.keys(nodes).sort(), ['Relay HTML', 'Scrape', 'Send', 'Trigger']);
  assert.equal(nodes.Scrape.parameters.apiOptionalParameters.apiAutoparse, false);
  assert.equal(nodes.Send.parameters.rawContentType, 'text/html');
  for (const [from, to] of [['Trigger', 'Scrape'], ['Scrape', 'Relay HTML'], ['Relay HTML', 'Send']]) {
    assert.equal(workflow.connections[from].main[0][0].node, to);
  }
  assert.equal(workflow.active, false);
  for (const node of workflow.nodes) assert.equal(node.credentials, undefined);
});
