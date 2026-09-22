# ADO admin request: Codex review permissions

Please use these steps to grant the minimum permissions needed to install and run Codex pull-request reviews for this repository.

## Scope

| Item | Value |
|---|---|
| Organization | [`LLMGenAITitaniumEngineering`](https://dev.azure.com/LLMGenAITitaniumEngineering) |
| Project | [`LLMGenAITitaniumEngineering`](https://dev.azure.com/LLMGenAITitaniumEngineering/LLMGenAITitaniumEngineering) |
| Repository | [`Titanium_Engineer-04_Team_3`](https://dev.azure.com/LLMGenAITitaniumEngineering/LLMGenAITitaniumEngineering/_git/Titanium_Engineer-04_Team_3) |
| Requesting user | `steven.espaillat@accenture.com` |
| Target branch | [`main`](https://dev.azure.com/LLMGenAITitaniumEngineering/LLMGenAITitaniumEngineering/_git/Titanium_Engineer-04_Team_3?version=GBmain) |

## 1. Confirm access level

1. Open **Organization settings > Users**.
2. Find `steven.espaillat@accenture.com`.
3. Confirm the access level is **Basic** or higher and that the user has access to the `LLMGenAITitaniumEngineering` project.

Stakeholder access is not sufficient for creating pull requests or updating work-item state and tags.

## 2. Grant repository permissions to Steven

1. Open [**Project settings > Repositories**](https://dev.azure.com/LLMGenAITitaniumEngineering/LLMGenAITitaniumEngineering/_settings/repositories).
2. Select **Repositories**.
3. Select **Titanium_Engineer-04_Team_3**.
4. Open **Security**.
5. Search for `steven.espaillat@accenture.com`.
6. Set these permissions to **Allow**:
   - **Read**
   - **Contribute**
   - **Create branch**
   - **Contribute to pull requests**
   - **Edit policies**
7. Save the changes.

These permissions allow normal branch pushes, pull-request creation and updates, and pull-request labels. They do not permit policy bypass or history rewriting. If practical, scope **Contribute** to the source-branch namespace used by Steven instead of granting it across protected branches.

Do not grant force-push, policy-bypass, repository administration, or branch-deletion permissions.

## 3. Grant pipeline permissions to Steven

1. Open [**Pipelines > Pipelines**](https://dev.azure.com/LLMGenAITitaniumEngineering/LLMGenAITitaniumEngineering/_build).
2. Open the **All pipelines** or root-folder security menu by selecting **More actions** (`…`) > **Manage security**.
3. Search for `steven.espaillat@accenture.com`.
4. Set these permissions to **Allow**:
   - **View build pipeline**
   - **Create build pipeline**
   - **Edit build pipeline**
   - **Queue builds**
5. Save the changes.

The account already appears to inherit View, Create, and Queue. **Edit build pipeline** is currently not set and must be granted.

## 4. Temporarily allow creation of the Classic build definition

The review uses a server-controlled Classic build definition so that a pull request cannot modify the review script that receives the OpenAI credential.

Recommended least-privilege procedure:

1. Open [**Project settings > Pipelines > Settings**](https://dev.azure.com/LLMGenAITitaniumEngineering/LLMGenAITitaniumEngineering/_settings/pipelinessettings).
2. Temporarily turn off **Disable creation of classic build pipelines**.
3. Tell Steven that pipeline creation is enabled.
4. Wait for Steven to confirm that the `Codex PR Review` definition has been created.
5. Turn **Disable creation of classic build pipelines** back on.

This avoids granting Steven broad project-administrator access. If Steven must perform the setting change himself, temporarily grant **Edit project-level information** or Project Administrators membership, then remove it after installation.

## 5. Grant work-item and tag permissions to Steven

1. Open [**Project settings > Project configuration > Areas**](https://dev.azure.com/LLMGenAITitaniumEngineering/LLMGenAITitaniumEngineering/_settings/work-team).
2. Open the security settings for the root `LLMGenAITitaniumEngineering` area path.
3. Search for `steven.espaillat@accenture.com`.
4. Set these permissions to **Allow**:
   - **View work items in this node**
   - **Edit work items in this node**
5. Ensure these permissions are inherited by child area paths.
6. In [**Project settings > Permissions**](https://dev.azure.com/LLMGenAITitaniumEngineering/LLMGenAITitaniumEngineering/_settings/permissions), ensure Steven or a group he belongs to has:
   - **Enumerate tag definitions**
   - **Create tag definition**
7. Save the changes.

These permissions allow viewing and updating work items, changing their state, adding existing tags, creating new tag names, and maintaining work-item links. They do not allow deleting work items, bypassing work-item rules, or changing the project process.

Do not grant:

- Delete and restore work items
- Permanently delete work items
- Bypass rules on work item updates
- Manage process or project-level work-item configuration
- Update or delete tag definitions unless separately required

## 6. Grant runtime permissions to the build-service identity

1. Return to [**Project settings > Repositories**](https://dev.azure.com/LLMGenAITitaniumEngineering/LLMGenAITitaniumEngineering/_settings/repositories), select **Titanium_Engineer-04_Team_3**, and open **Security**.
2. Search for the project build-service identity, normally:

   `LLMGenAITitaniumEngineering Build Service (LLMGenAITitaniumEngineering)`

3. Set these permissions to **Allow**:
   - **Read**
   - **Contribute to pull requests**
4. Save the changes.

Do not grant the build service:

- Contribute/push
- Create branch or tag
- Force push
- Edit policies
- Bypass policies
- Manage permissions
- Repository administration

These two permissions let the project-scoped `System.AccessToken` read the PR and publish the Codex review thread and status. They do not let the pipeline push code.

## 7. Confirm project pipeline security settings

Under [**Project settings > Pipelines > Settings**](https://dev.azure.com/LLMGenAITitaniumEngineering/LLMGenAITitaniumEngineering/_settings/pipelinessettings), confirm:

- **Limit job authorization scope to current project** is enabled.
- Repository protection/referenced-repository restrictions remain enabled.
- Access to secrets from fork builds remains restricted.

No organization-wide or collection-scoped build token is required.

## 8. Confirm credential scopes

If Steven uses an Azure DevOps PAT or OAuth token instead of an interactive Azure CLI login, restrict it to:

- **Code: Read & write** (`vso.code_write`)
- **Work Items: Read & write** (`vso.work_write`)
- **Build: Read & execute** (`vso.build_execute`), for pipeline installation and management
- **Project and Team: Read & write** (`vso.project_write`) only if Steven, rather than an administrator, will change the Classic-pipeline project setting

A token never grants more access than its owner's Azure DevOps security permissions. Store it as a secret and do not place it in repository files.

## 9. Reference links

- [Azure DevOps permissions and groups reference](https://learn.microsoft.com/en-us/azure/devops/organizations/security/permissions?view=azure-devops)
- [Set Git repository permissions](https://learn.microsoft.com/en-us/azure/devops/repos/git/set-git-repository-permissions?view=azure-devops)
- [Create pull requests](https://learn.microsoft.com/en-us/azure/devops/repos/git/pull-requests?view=azure-devops)
- [PR label REST API](https://learn.microsoft.com/en-us/rest/api/azure/devops/git/pull-request-labels/create?view=azure-devops-rest-7.1)
- [Set work-tracking and tag permissions](https://learn.microsoft.com/en-us/azure/devops/organizations/security/set-permissions-access-work-tracking?view=azure-devops)
- [Link work items to development objects](https://learn.microsoft.com/en-us/azure/devops/boards/backlogs/connect-work-items-to-git-dev-ops?view=azure-devops)
- [Pipeline permissions](https://learn.microsoft.com/en-us/azure/devops/pipelines/policies/permissions?view=azure-devops)
- [Pipeline job access tokens](https://learn.microsoft.com/en-us/azure/devops/pipelines/process/access-tokens?view=azure-devops)

## 10. Notify Steven

After completing the steps, send this confirmation:

> Repository, pull-request, work-item, tag, pipeline, and build-service permissions are configured for `steven.espaillat@accenture.com` on `Titanium_Engineer-04_Team_3`. Classic build-definition creation is temporarily enabled and may now be used to create `Codex PR Review`.

Steven will then create the pipeline, store its dedicated OpenAI key, install the non-blocking build-validation policy on `main`, verify it, and confirm when Classic pipeline creation can be disabled again.
