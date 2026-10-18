# PAK install: requests made by the UI

Recorded on 2026-10-18 while installing `vCommunity_0.4.1.pak` on `https://vcf-m02-ops01.acepod.com` through **Administration → Integrations → Repository → Add**, with both **Install the PAK file even if it is already installed** and **Ignore the PAK file signature checking** ticked. The install finished with `Applied and Cleaned (Completed)`, and the Repository tab then listed VCF vCommunity Adapter 0.4.1.

## How this was captured

- The Repository wizard runs in the legacy UI inside the `ops_iframe` frame (`/vcf-operations/plug/ops/index.action`). Relative URLs below resolve against `https://<host>/vcf-operations/plug/ops/`.
- Request bodies came from hooks on `XMLHttpRequest`, `fetch` and `HTMLFormElement.submit` in the page and the frame. Full URLs, status codes and the upload response came from the browser's network log.
- Header names are the ones the page set itself with `setRequestHeader`. Their values were not recorded. Cookies are sent automatically and are all HttpOnly, so their names are not visible to page script and are not listed here.
- **Not recorded:** cookie values, auth header values and the CSRF token value. The CSRF token is the `secureToken` field (shown as `<secureToken>`). It is one value per login session, sent in every POST body and twice in the upload form.
- Unrelated background requests are left out (`getCollectionNotifications`, `stateManager.action?mainAction=getState`, `problemalerts.action?mainAction=checkForNewSystemAlerts`).

## Repeating this capture

These notes apply when Claude drives the install in the built-in browser of the Claude desktop app.

1. **A person has to pick the PAK.** BROWSE opens the operating system's file dialog. The built-in browser cannot attach files or control that dialog, so after Claude opens **Add**, someone has to click BROWSE and choose the `.pak` file. Claude can do the rest.
2. **Add the logging hooks after the Add dialog opens and before clicking UPLOAD.** The network log shows URLs, status codes and response bodies, but not request bodies or form fields, which is why the hooks are needed. Hook both the top window and the `ops_iframe` window, because the wizard's requests come from the frame. Hooks live in page memory: any reload or navigation removes them, so add them again before the next step you want recorded.
3. **Expect an "unsigned pack" confirmation after NEXT** when signature checking is ignored and the PAK is unsigned. Answer YES to reach the EULA page.
4. **Remove the token before saving.** The hooks capture the real `secureToken` value in every POST body. Replace it with `<secureToken>` before writing anything to the repo.

## Sequence

| # | Step | Method | URL | Count |
|---|------|--------|-----|-------|
| 1 | Click UPLOAD | POST | `utility.action` (`mainAction=prepareFileUpload`) | 1 |
| 2 | Click UPLOAD | POST | `admin/services/solution/upload?uploadId=…&ignoreSignatureChecking=true` (multipart form) | 1 |
| 3 | Upload progress | GET | `admin/services/solution/upload?…&progress=true` | 34, about every 1.05 s |
| 4 | Upload done | POST | `solution.action` (`mainAction=getSolutionVersion`) | 1 |
| 5 | NEXT → *unsigned pack?* YES → EULA page | POST | `solution.action` (`mainAction=getLicenseAgreement`) | 1 |
| 6 | Accept EULA → NEXT | POST | `solution.action` (`mainAction=install`) | 1 |
| 7 | Install progress | POST | `solution.action` (`mainAction=getInstallStatus`) | 16, about every 6.7 s |

Ticking the EULA box and the "unsigned pack" confirmation dialog made no requests. EULA acceptance is not sent to the server; `mainAction=install` is the only call after it. The confirmation dialog appears because the upload response reports `"signingStatus":"NotSigned"`.

## 1. Prepare upload

- **URL:** `https://vcf-m02-ops01.acepod.com/vcf-operations/plug/ops/utility.action`
- **Method:** POST (XHR)
- **Query parameters:** none
- **Headers set by the page:** `Content-Type`, `X-Requested-With`
- **Body (urlencoded):**

  | Field | Value |
  |-------|-------|
  | `mainAction` | `prepareFileUpload` |
  | `currentComponentInfo` | `TODO` |
  | `secureToken` | `<secureToken>` |

- **Response:** 200

  ```json
  {"success":true}
  ```

## 2. Upload the PAK

- **URL:** `https://vcf-m02-ops01.acepod.com/vcf-operations/plug/ops/admin/services/solution/upload`
- **Method:** POST, from a classic `form.submit()` into a hidden iframe (target `ext-element-84`), not XHR
- **Content type:** `multipart/form-data`
- **Query parameters:**

  | Parameter | Value | Notes |
  |-----------|-------|-------|
  | `uploadId` | `1792296567666` | Client-generated: the `Date.now()` in ms at the moment UPLOAD was clicked. Reused by the progress polls. |
  | `ignoreSignatureChecking` | `true` | From the "Ignore the PAK file signature checking" box |

- **Form fields, in order:**

  | Field | Value | Notes |
  |-------|-------|-------|
  | `secureToken` | `<secureToken>` | |
  | `forceUpload` | `true` | From the "Install the PAK file even if it is already installed" box |
  | `forceContent` | `false` | |
  | `undefined` | `on` | The two checkboxes have no `name`, so the browser sends them as `undefined=on`. Harmless noise; the real flags are `forceUpload` and `ignoreSignatureChecking`. |
  | `undefined` | `on` | (second checkbox) |
  | `solution` | file `vCommunity_0.4.1.pak`, 443328 bytes, no content type set by the browser | The PAK itself |
  | `currentComponentInfo` | `TODO` | |
  | `secureToken` | `<secureToken>` | Sent a second time |

- **Response:** 200 (the browser shows it as `ignoreSignatureChecking=REDACTED` in the network log; the real value was `true`). `solutionDescription` is shortened here:

  ```json
  {
    "pakId": "iSDKvCommunity-041",
    "solutionName": "VCF vCommunity Adapter",
    "solutionVersion": "0.4.1",
    "solutionFilename": "vCommunity_0.4.1.pak",
    "solutionDescription": "This Management Pack provides a framework to bring your own content … More details: <a href=\"https://github.com/e1-rahabok/VCF-vCommunity-Adapter\" …>…</a>",
    "signingStatus": "NotSigned",
    "estimatedInstallTime": "Not available",
    "containsSystemUpdate": false,
    "clusterBringOffline": false,
    "clusterRestartRequired": false,
    "adminRestartRequired": false,
    "osRestartRequired": false,
    "success": true
  }
  ```

## 3. Upload progress (polled)

- **URL:** `https://vcf-m02-ops01.acepod.com/vcf-operations/plug/ops/admin/services/solution/upload`
- **Method:** GET (XHR)
- **Headers set by the page:** `X-Requested-With`
- **Query parameters:**

  | Parameter | Value | Notes |
  |-----------|-------|-------|
  | `_dc` | e.g. `1792296569813` | ExtJS cache-buster, `Date.now()` per call |
  | `uploadId` | `1792296567666` | Same as step 2 |
  | `progress` | `true` | |
  | `currentComponentInfo` | `TODO` | |

- **Response:** 200. All 34 polls returned the same body while the server staged the file:

  ```json
  {"uploadId":"1792296567666","uploadInProgress":true,"percentComplete":100,"bytesRead":null,"totalBytes":null,"message":"Staging...","isRestarting":false,"restartingMessage":"","seconds":0}
  ```

  Polling stopped when the multipart POST in step 2 returned (about 37 s after UPLOAD). The UI goes by that response, not by a final progress body.

## 4. Get installed version

- **URL:** `https://vcf-m02-ops01.acepod.com/vcf-operations/plug/ops/solution.action`
- **Method:** POST (XHR)
- **Headers set by the page:** `Content-Type`, `X-Requested-With`
- **Body (urlencoded):**

  | Field | Value |
  |-------|-------|
  | `mainAction` | `getSolutionVersion` |
  | `solutionName` | `iSDKvCommunity` (the `pakId` without its version suffix) |
  | `currentComponentInfo` | `TODO` |
  | `secureToken` | `<secureToken>` |

- **Response:** 200. 0.4.1 was already installed, but the response carries no version:

  ```json
  {"success":true}
  ```

## 5. Get EULA

- **URL:** `https://vcf-m02-ops01.acepod.com/vcf-operations/plug/ops/solution.action`
- **Method:** POST (XHR)
- **Headers set by the page:** `Content-Type`, `X-Requested-With`
- **Body (urlencoded):**

  | Field | Value |
  |-------|-------|
  | `mainAction` | `getLicenseAgreement` |
  | `currentComponentInfo` | `TODO` |
  | `secureToken` | `<secureToken>` |

- **Response:** 200. One field, `licenseText`, holding the pack's EULA text (this pack's configuration steps, starting `=== CONFIGURATION STEPS ===`):

  ```json
  {"licenseText":"=== CONFIGURATION STEPS ===\r\n * Once installed, do the following: …"}
  ```

  It takes no `pakId`: the server returns the EULA of the PAK staged in this session.

## 6. Start install

- **URL:** `https://vcf-m02-ops01.acepod.com/vcf-operations/plug/ops/solution.action`
- **Method:** POST (XHR)
- **Headers set by the page:** `Content-Type`, `X-Requested-With`
- **Body (urlencoded):**

  | Field | Value |
  |-------|-------|
  | `mainAction` | `install` |
  | `currentComponentInfo` | `TODO` |
  | `secureToken` | `<secureToken>` |

- **Response:** 200

  ```json
  {}
  ```

  No `pakId` or flags are sent. The server installs whatever was staged by the upload in this session, with the `forceUpload` and `ignoreSignatureChecking` choices made in step 2.

## 7. Install status (polled)

- **URL:** `https://vcf-m02-ops01.acepod.com/vcf-operations/plug/ops/solution.action`
- **Method:** POST (XHR)
- **Headers set by the page:** `Content-Type`, `X-Requested-With`
- **Body (urlencoded):**

  | Field | Value |
  |-------|-------|
  | `mainAction` | `getInstallStatus` |
  | `currentComponentInfo` | `TODO` |
  | `secureToken` | `<secureToken>` |

- **Response:** 200. 16 polls over about 100 s. The states seen, in order:

  ```json
  {"statuses":[{"nodeAddress":"vcf-m02-ops01.acepod.com","state":"Staged","status":"Candidate"}],"completed":false}
  {"statuses":[{"nodeAddress":"vcf-m02-ops01.acepod.com","state":"Preapply Validated","status":"Candidate"}],"completed":false}
  {"statuses":[{"nodeAddress":"vcf-m02-ops01.acepod.com","state":"Applied Adapter Pre Script","status":"Candidate"}],"completed":false}
  {"statuses":[{"nodeAddress":"vcf-m02-ops01.acepod.com","state":"Applied Adapter","status":"Candidate"}],"completed":false}
  {"statuses":[{"nodeAddress":"vcf-m02-ops01.acepod.com","state":"Applied and Cleaned","status":"Completed"}],"completed":true}
  ```

  Polling stops on `"completed":true`, and the wizard then shows FINISH. There is one entry in `statuses` per cluster node; this instance has one node.
