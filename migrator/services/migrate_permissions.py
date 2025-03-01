from collections import defaultdict

from django.db.models import OuterRef, Exists

from migrator.utils import paginated_query
from posts.models import Post
from projects.models import Project, ProjectUserPermission
from projects.permissions import ObjectPermission
from utils.dtypes import flatten

# TODO: what to do with MP/Site Main project type? Do we want
#  to keep it as separate type or merge with categories/topics?


# These types were merged with project during metaculus refactoring
# So we need to exclude them since we kept same ids for old Projects table rows,
# but autogenerated ids for these types
NON_PROJECT_TYPES = [
    Project.ProjectTypes.CATEGORY,
    Project.ProjectTypes.TAG,
    Project.ProjectTypes.TOPIC,
]


def convert_question_permissions(code: int):
    return {
        524287: ObjectPermission.ADMIN,
        294941: ObjectPermission.FORECASTER,
        # private_project_perms, probably an admin
        65535: ObjectPermission.ADMIN,
        # moderator_perms
        316860: ObjectPermission.CURATOR,
        # 360477
        # <Original Permissions:PREDICT|COMMENT_READ|COMMENT_POST|COMMENT_EDIT|VIEW_COMMUNITY_PRED|VIEW_METACULUS_PRED|VIEW_METACULUS_PRED_AFTER_CLOSE: 360477>
        360477: ObjectPermission.FORECASTER,
        # 491549
        # <Original Permissions:PREDICT|COMMENT_READ|COMMENT_POST|COMMENT_EDIT|VIEW_COMMUNITY_PRED|VIEW_METACULUS_PRED|VIEW_COMMUNITY_PRED_AFTER_CLOSE|VIEW_METACULUS_PRED_AFTER_CLOSE: 491549>
        491549: ObjectPermission.FORECASTER,
        # 491933
        # <Original Permissions:PREDICT|COMMENT_READ|COMMENT_POST|COMMENT_EDIT|EDIT_PENDING_CONTENT|EDIT_UPCOMING_CONTENT|VIEW_COMMUNITY_PRED|VIEW_METACULUS_PRED|VIEW_COMMUNITY_PRED_AFTER_CLOSE|VIEW_METACULUS_PRED_AFTER_CLOSE: 491933>
        491933: ObjectPermission.FORECASTER,
        # <Original Permissions:PREDICT|COMMENT_READ|COMMENT_POST|VIEW_COMMUNITY_PRED|VIEW_METACULUS_PRED|VIEW_COMMUNITY_PRED_AFTER_CLOSE|VIEW_METACULUS_PRED_AFTER_CLOSE: 491533>
        491533: ObjectPermission.FORECASTER,
        # Should be probably MOD, but will see
        # <Original Permissions:PREDICT|RESOLVE|COMMENT_READ|COMMENT_POST|COMMENT_EDIT|COMMENT_MOD|EDIT_PENDING_CONTENT|EDIT_UPCOMING_CONTENT|EDIT_CATEGORIES|CHANGE_PENDING_STATUS|CROSSPOST|VIEW_COMMUNITY_PRED|VIEW_METACULUS_PRED_AFTER_CLOSE: 316863>
        316863: ObjectPermission.CURATOR,
        # <Original Permissions:COMMENT_READ|COMMENT_POST|COMMENT_EDIT|COMMENT_MOD|EDIT_PENDING_CONTENT|EDIT_UPCOMING_CONTENT|EDIT_CATEGORIES|CHANGE_PENDING_STATUS|VIEW_COMMUNITY_PRED|VIEW_METACULUS_PRED|VIEW_METACULUS_PRED_AFTER_CLOSE: 366012>
        366012: ObjectPermission.CURATOR,
        # <Original Permissions:COMMENT_READ|COMMENT_POST|COMMENT_EDIT|COMMENT_MOD|EDIT_PENDING_CONTENT|EDIT_UPCOMING_CONTENT|EDIT_CATEGORIES|CHANGE_PENDING_STATUS|CROSSPOST|VIEW_COMMUNITY_PRED|VIEW_METACULUS_PRED|VIEW_METACULUS_PRED_AFTER_CLOSE: 382396>
        382396: ObjectPermission.CURATOR,
        # viewer_perms
        294940: ObjectPermission.VIEWER,
        # author_perms
        297180: ObjectPermission.CREATOR,
        # <Original Permissions:COMMENT_READ|COMMENT_POST|COMMENT_EDIT|VIEW_COMMUNITY_PRED|VIEW_METACULUS_PRED_AFTER_CLOSE|VIEW_AUTHORS_ANONYMIZED: 1343516>
        1343516: ObjectPermission.FORECASTER,
    }.get(code)


def convert_project_permissions(code):
    return {
        # none. But this does not hide anything, project is still visible for the user
        0: ObjectPermission.VIEWER,
        # SUGGEST_NEW_QUESTION
        2: ObjectPermission.VIEWER,
        # full_perms
        31: ObjectPermission.ADMIN,
        # private_project_perms
        15: ObjectPermission.ADMIN,
        # <ProjectPermissions.SUGGEST_NEW_QUESTION|ADD_CROSSPOSTED_QUESTION: 6>
        6: ObjectPermission.VIEWER,
    }.get(code)


def migrate_common_permissions():
    """
    Migrates permissions from regular projects
    """

    # Extracting ids of entities that was the only Project types in the old Metac
    # And exclude PersonalProjects since they will be migrated in a separate function
    project_ids = Project.objects.exclude(
        type__in=NON_PROJECT_TYPES + [Project.ProjectTypes.PERSONAL_PROJECT]
    ).values_list("id", flat=True)
    user_project_perms = []
    project_question_permissions_map = defaultdict(list)

    for obj in paginated_query(
        "SELECT * FROM metac_project_questionprojectpermissions"
    ):
        project_question_permissions_map[obj["project_id"]].append(obj)

    total_missed_project_ids = set()
    total_missed_project_types = set()

    # Migrating User<>Project ad-hoc permissions
    for user_project_perm_obj in paginated_query(
        """
        SELECT 
           upp.*, p.default_question_permissions, p.default_project_permissions, p.type
        FROM metac_project_userprojectpermissions upp
        JOIN metac_project_project p 
        ON upp.project_id = p.id
        WHERE p.type != 'PP'
        """
    ):
        # New app merges Project & Categories & Tags etc.
        # Tournaments & QS & PP were migrated to Project model with the same Ids as the old ones.
        # All further instances in Project table (e.g. tags) are created with next id autoinc sequence
        # So we need to ensure we don't link permissions to newly generated entities
        # that are not related to the old Project table
        if user_project_perm_obj["project_id"] not in project_ids:
            total_missed_project_ids.add(user_project_perm_obj["project_id"])
            total_missed_project_types.add(user_project_perm_obj["type"])

            continue

        default_question_permissions = user_project_perm_obj[
            "default_question_permissions"
        ]

        # Get override permission and ensure it includes default one
        question_permission_code = user_project_perm_obj["question_permissions"]

        if pq_permissions := project_question_permissions_map[
            user_project_perm_obj["project_id"]
        ]:
            all_permission = {obj["permissions"] for obj in pq_permissions}

            # Performing odd permissions check
            # Taken from the original project
            # To ensure we can't override permissions declared in ProjectQuestion.permissions
            for permission in all_permission:
                bitcheck = permission & (
                    question_permission_code | default_question_permissions
                )

                if bitcheck != question_permission_code and bitcheck != (
                    question_permission_code | default_question_permissions
                ):
                    print(
                        f"QuestionProjectPermission.permission affected "
                        f"project: {user_project_perm_obj['project_id']}"
                    )

        question_permission = convert_question_permissions(question_permission_code)

        if question_permission:
            user_project_perms.append(
                ProjectUserPermission(
                    user_id=user_project_perm_obj["user_id"],
                    project_id=user_project_perm_obj["project_id"],
                    permission=question_permission,
                )
            )

    ProjectUserPermission.objects.bulk_create(
        user_project_perms, batch_size=50_000, ignore_conflicts=True
    )
    print(
        f"Missed projects: {len(total_missed_project_ids)} "
        f"of the following OLD types: {total_missed_project_types}"
    )


def migrate_personal_projects():
    """
    Migrating personal projects of users
    """

    # Seems like old metac was creating a new Personal Project for each Private Question
    post_ids = Post.objects.values_list("id", flat=True)
    questions_map = {}
    project_user_mapping = defaultdict(list)

    for perm_obj in paginated_query(
        "SELECT * FROM metac_project_userprojectpermissions"
    ):
        project_user_mapping[perm_obj["project_id"]].append(perm_obj)

    for row in paginated_query(
        "SELECT p.id, p.default_question_permissions, qpp.question_id, qpp.permissions, q.author_id "
        "FROM metac_project_project p "
        "JOIN metac_project_questionprojectpermissions qpp "
        "ON qpp.project_id = p.id "
        "JOIN metac_question_question q ON q.id = qpp.question_id "
        "WHERE p.type = 'PP'"
    ):
        project_id = row["id"]
        question_id = row["question_id"]

        if question_id not in questions_map:
            questions_map[question_id] = {
                "id": question_id,
                "author_id": row["author_id"],
                "projects": [],
            }

        questions_map[question_id]["projects"].append(
            {
                "id": project_id,
                "permissions": row["permissions"],
                "default_question_permissions": row["default_question_permissions"],
                "users": project_user_mapping[project_id],
            }
        )

    # user_id -> Project()
    questions_404 = 0
    projects_to_create = []
    project_user_permissions_to_create = []
    post_projects_to_create = []

    # Extract Project<>User permissions
    for question_id, question_obj in questions_map.items():
        if question_id not in post_ids:
            questions_404 += 1
            continue

        # Creating a private project
        private_project = Project(
            name="Personal List",
            type=Project.ProjectTypes.PERSONAL_PROJECT,
            created_by_id=question_obj["author_id"],
            default_permission=None,
        )
        projects_to_create.append(private_project)

        # Add Post<>Project relations
        post_projects_to_create.append(
            Post.projects.through(project=private_project, post_id=question_id)
        )

        users_have_access = flatten([p["users"] for p in question_obj["projects"]])

        # Sharing with co-authors
        for user in users_have_access:
            # If user is not author means this Private Question was just shared with them
            # All such users have `65535 (private_project_perms OR coauthor
            # (results after combination of this ProjectQuestion.permission AND UserProject.question_permission attrs))`
            # permissions for the question.
            # Setting non-authors to `AUTHOR` to keep ability to edit materials
            #
            # Skipping authors since they have access to their posts by default
            if user["user_id"] != question_obj["author_id"]:
                project_user_permissions_to_create.append(
                    ProjectUserPermission(
                        project=private_project,
                        user_id=user["user_id"],
                        # Should be discussed separately
                        permission=ObjectPermission.CREATOR,
                    )
                )

    Project.objects.bulk_create(projects_to_create, batch_size=20_000)
    ProjectUserPermission.objects.bulk_create(
        project_user_permissions_to_create, batch_size=20_000
    )
    Post.projects.through.objects.bulk_create(
        post_projects_to_create, batch_size=20_000
    )

    print("Mapped Private Project Permissions!")

    if questions_404:
        print(
            f"Couldn't find {questions_404}/{len(questions_map)} questions, "
            f"probably their types have not been migrated yet"
        )


def migrate_post_default_project():
    # Assign default_project to the Posts
    # Based on the most Public Project they have
    total_posts_without_projects = 0
    posts_to_update = []

    def prioritize_projects_for_default(prj: Project):
        permission_code = (
            ObjectPermission.get_permissions_rank().get(prj.default_permission) or 0
        )

        if prj.type == Project.ProjectTypes.PERSONAL_PROJECT:
            # Deprioritize personal projects VS other projects with the same permissions level
            permission_code -= 0.01

        return permission_code

    for post in Post.objects.prefetch_related("projects").iterator(chunk_size=10_000):
        sorted_projects = sorted(
            [
                project
                for project in post.projects.all()
                if project.type not in NON_PROJECT_TYPES
            ],
            key=prioritize_projects_for_default,
        )

        if sorted_projects:
            # Taking the most "Open" project as the default one
            post.default_project = sorted_projects[-1]
            posts_to_update.append(post)
        else:
            total_posts_without_projects += 1

    Post.objects.bulk_update(
        posts_to_update, batch_size=50_000, fields=["default_project"]
    )

    print(
        f"Posts without Projects: {total_posts_without_projects}. "
        f"Probably some old Project types have not been migrated yet"
    )
    print(f"Migrated default_project for {len(posts_to_update)} posts")


def deduplicate_default_project_and_m2m():
    """
    In some cases we might have same project appeared in both Post.default_project and PostProject m2m table.
    This function removes redundant m2m relations
    """

    PostProject = Post.projects.through

    subquery = Post.objects.filter(
        id=OuterRef("post_id"), default_project=OuterRef("project_id")
    )

    PostProject.objects.filter(Exists(subquery)).delete()


def migrate_permissions():
    migrate_personal_projects()
    migrate_common_permissions()
    migrate_post_default_project()
    deduplicate_default_project_and_m2m()
