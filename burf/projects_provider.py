from google.cloud import resourcemanager_v3


class ProjectsProvider:
    def __init__(self) -> None:
        pass
        # self.credentials = credentials

    def get_gcloud_projects(self):
        client = resourcemanager_v3.ProjectsClient()
        request = resourcemanager_v3.ListProjectsRequest()

        print(client.list_projects(request=request))

        # project_list = []
        # for project in projects:
        #     project_list.append(project.project_id)

        # return project_list


print(ProjectsProvider().get_gcloud_projects())
