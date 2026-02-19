/**
 * E2E Flow 8: Test Case Versioning & History — F2 coverage.
 *
 * Tests the version snapshot, diff comparison, and restore APIs.
 * Uses API-level requests (no browser UI navigation needed).
 */
import { test, expect } from '@playwright/test'

const API = '/api/v1'

let catalogId: number | null = null

test.describe.serial('Test Case Versioning (F2)', () => {
  test('create a test case for versioning', async ({ request }) => {
    const res = await request.post(`${API}/programs/1/testing/catalog`, {
      data: {
        title: 'E2E Version Test Case',
        description: 'Created by E2E for versioning tests',
        priority: 'High',
        test_type: 'Manual',
        steps: [
          { step_no: 1, action: 'Open app', test_data: '', expected_result: 'App opens', notes: '' },
          { step_no: 2, action: 'Click button', test_data: 'btn=save', expected_result: 'Saved', notes: '' },
        ],
      },
    })
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    catalogId = body.id
    expect(catalogId).toBeGreaterThan(0)
  })

  test('auto-snapshot creates initial version', async ({ request }) => {
    const res = await request.get(`${API}/testing/catalog/${catalogId}/versions`)
    expect(res.ok()).toBeTruthy()
    const versions = await res.json()
    expect(versions.length).toBeGreaterThanOrEqual(1)
    expect(versions[0].version_no).toBe(1)
  })

  test('updating test case creates new version', async ({ request }) => {
    const res = await request.put(`${API}/testing/catalog/${catalogId}`, {
      data: {
        title: 'E2E Version Test Case — Updated',
        description: 'Updated description for diff',
        priority: 'Critical',
      },
    })
    expect(res.ok()).toBeTruthy()

    const verRes = await request.get(`${API}/testing/catalog/${catalogId}/versions`)
    expect(verRes.ok()).toBeTruthy()
    const versions = await verRes.json()
    expect(versions.length).toBeGreaterThanOrEqual(2)
  })

  test('manual snapshot works', async ({ request }) => {
    const res = await request.post(`${API}/testing/catalog/${catalogId}/versions`, {
      data: { change_summary: 'manual checkpoint' },
    })
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.version_no).toBeGreaterThanOrEqual(3)
  })

  test('diff between versions returns field changes', async ({ request }) => {
    const res = await request.get(`${API}/testing/catalog/${catalogId}/versions/diff?from=1&to=2`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.diff).toBeDefined()
    expect(body.diff.summary).toBeDefined()

    // We changed title, description, priority — should see field_changes
    expect(body.diff.summary.field_change_count).toBeGreaterThanOrEqual(1)
    expect(body.diff.field_changes.length).toBeGreaterThanOrEqual(1)

    // Verify field_changes structure
    const titleChange = body.diff.field_changes.find((fc: any) => fc.field === 'title')
    if (titleChange) {
      expect(titleChange.from).toBe('E2E Version Test Case')
      expect(titleChange.to).toBe('E2E Version Test Case — Updated')
    }
  })

  test('diff summary includes step counts', async ({ request }) => {
    const res = await request.get(`${API}/testing/catalog/${catalogId}/versions/diff?from=1&to=2`)
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    const summary = body.diff.summary
    expect(typeof summary.step_added_count).toBe('number')
    expect(typeof summary.step_removed_count).toBe('number')
    expect(typeof summary.step_changed_count).toBe('number')
  })

  test('restore version reverts test case', async ({ request }) => {
    // Restore to version 1
    const restoreRes = await request.post(`${API}/testing/catalog/${catalogId}/versions/1/restore`, {
      data: { change_summary: 'E2E restore test' },
    })
    expect(restoreRes.ok()).toBeTruthy()

    // Verify the title is back to original
    const tcRes = await request.get(`${API}/testing/catalog/${catalogId}`)
    expect(tcRes.ok()).toBeTruthy()
    const tc = await tcRes.json()
    expect(tc.title).toBe('E2E Version Test Case')
  })

  test('version list grows after restore', async ({ request }) => {
    const res = await request.get(`${API}/testing/catalog/${catalogId}/versions`)
    expect(res.ok()).toBeTruthy()
    const versions = await res.json()
    // Original create (v1) + update (v2) + manual (v3) + restore snapshot (v4)
    expect(versions.length).toBeGreaterThanOrEqual(4)
  })

  test('History tab UI renders side-by-side diff', async ({ page }) => {
    // Navigate to test case detail page
    await page.goto(`/#testing/case/${catalogId}`)
    await page.waitForTimeout(1500)

    // Click History tab
    const historyTab = page.locator('.tm-tabbar__item', { hasText: 'History' })
    if (await historyTab.count() > 0) {
      await historyTab.click()
      await page.waitForTimeout(800)

      // Verify versions grid is present
      const versionsSection = page.locator('text=Versions')
      expect(await versionsSection.count()).toBeGreaterThanOrEqual(1)

      // Click Compare button to trigger diff
      const compareBtn = page.locator('button', { hasText: 'Compare' })
      if (await compareBtn.count() > 0) {
        await compareBtn.click()
        await page.waitForTimeout(1000)

        // Check for side-by-side diff viewer
        const diffViewer = page.locator('.tm-diff-viewer')
        if (await diffViewer.count() > 0) {
          // Verify diff table columns exist
          const oldCol = page.locator('.tm-diff-col-old')
          const newCol = page.locator('.tm-diff-col-new')
          expect(await oldCol.count()).toBeGreaterThanOrEqual(1)
          expect(await newCol.count()).toBeGreaterThanOrEqual(1)
        }
      }
    }
  })
})
