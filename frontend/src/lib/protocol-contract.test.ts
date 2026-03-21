import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { rendererRegistry } from '@/components/renderer-registry'
import { registeredActionTypes } from '@/lib/action-registry'

function readBackendContractSource() {
  return readFileSync(resolve(process.cwd(), '../app/services/crm_service.py'), 'utf-8')
}

function extractBackendComponentTypes(source: string) {
  return Array.from(source.matchAll(/component_type="([^"]+)"/g), (match) => match[1]).sort()
}

function extractSupportedActions(source: string) {
  const block = source.match(/SUPPORTED_ACTIONS = \[(.*?)\]\n/s)
  if (!block) {
    throw new Error('SUPPORTED_ACTIONS block not found in crm_service.py')
  }

  return Array.from(block[1].matchAll(/"([^"]+)"/g), (match) => match[1]).sort()
}

describe('protocol contract sync', () => {
  it('registers renderers for every backend component type', () => {
    const backendSource = readBackendContractSource()
    const backendTypes = Array.from(new Set(extractBackendComponentTypes(backendSource)))
    const registeredTypes = new Set(Object.keys(rendererRegistry))

    const missing = backendTypes.filter((componentType) => !registeredTypes.has(componentType))

    expect(missing).toEqual([])
  })

  it('registers handlers for every backend supported action', () => {
    const backendSource = readBackendContractSource()
    const supportedActions = extractSupportedActions(backendSource)
    const registeredTypes = new Set(registeredActionTypes)

    const missing = supportedActions.filter((actionType) => !registeredTypes.has(actionType))

    expect(missing).toEqual([])
  })
})
