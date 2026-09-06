import test from 'node:test';
import assert from 'node:assert/strict';
import {createMockRecords} from './mock-adapter.js';
test('mock adapter preserves filenames and exposes duplicate/review states',()=>{const records=createMockRecords([{name:'one.png',size:100,type:'image/png'},{name:'two.jpg',size:200,type:'image/jpeg'},{name:'three.webp',size:300,type:'image/webp'}]);assert.equal(records[0].name,'one.png');assert.equal(records[1].status,'duplicate');assert.equal(records[2].status,'review_required');assert.equal(records[0].preservation,'Original locked');});
