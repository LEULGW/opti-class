import csv
import requests

url = "https://www.ratemyprofessors.com/graphql"

query_template = """query TeacherSearchResultsPageQuery(
  $query: TeacherSearchQuery!
  $schoolID: ID
  $includeSchoolFilter: Boolean!
) {
  search: newSearch {
    ...TeacherSearchPagination_search_2MvZSr
  }
  school: node(id: $schoolID) @include(if: $includeSchoolFilter) {
    __typename
    ... on School {
      name
      ...StickyHeaderContent_school
    }
    id
  }
}

fragment CardFeedback_teacher on Teacher {
  wouldTakeAgainPercent
  avgDifficulty
}

fragment CardName_teacher on Teacher {
  firstName
  lastName
}

fragment CardSchool_teacher on Teacher {
  department
  school {
    name
    id
  }
}

fragment CompareSchoolLink_school on School {
  legacyId
}

fragment HeaderDescription_school on School {
  name
  city
  state
  legacyId
  ...RateSchoolLink_school
  ...CompareSchoolLink_school
}

fragment HeaderRateButton_school on School {
  ...RateSchoolLink_school
  ...CompareSchoolLink_school
}

fragment RateSchoolLink_school on School {
  legacyId
  lockStatus
}

fragment StickyHeaderContent_school on School {
  name
  ...HeaderDescription_school
  ...HeaderRateButton_school
}

fragment TeacherBookmark_teacher on Teacher {
  id
  isSaved
}

fragment TeacherCard_teacher on Teacher {
  id
  legacyId
  avgRating
  numRatings
  ...CardFeedback_teacher
  ...CardSchool_teacher
  ...CardName_teacher
  ...TeacherBookmark_teacher
}

fragment TeacherSearchPagination_search_2MvZSr on newSearch {
  teachers(query: $query, first: 100, after: "<CURSOR>") {
    didFallback
    edges {
      cursor
      node {
        ...TeacherCard_teacher
        id
        __typename
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
    resultCount
    filters {
      field
      options {
        value
        id
      }
    }
  }
}
"""

headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Origin": "https://www.ratemyprofessors.com",
}

variables = {
    "query": {"text": "", "schoolID": "U2Nob29sLTQyMQ==", "fallback": True},
    "schoolID": "U2Nob29sLTQyMQ==",
    "includeSchoolFilter": True,
}

all_teachers = []
has_next_page = True
cursor = ""

print("Fetching professors...")

# Loop through all pages
while has_next_page:
    # Insert the current cursor into the query template
    current_query = query_template.replace("<CURSOR>", cursor)

    payload = {
        "query": current_query,
        "operationName": "TeacherSearchResultsPageQuery",
        "variables": variables,
    }

    response = requests.post(url, json=payload, headers=headers)
    data = response.json()

    # Extract teacher nodes and page info
    teacher_data = data["data"]["search"]["teachers"]
    edges = teacher_data["edges"]
    all_teachers.extend(edges)

    page_info = teacher_data["pageInfo"]
    has_next_page = page_info["hasNextPage"]
    cursor = page_info["endCursor"]

    print(f"Collected {len(all_teachers)} professors so far...")

# Write all collected professors to the CSV
with open(
    "/Users/leul/opti-class/backend/data/processed/howard_professors_rmp.csv", "w", newline="", encoding="utf-8"
) as file:
    writer = csv.DictWriter(
        file,
        fieldnames=[
            "Name",
            "Department",
            "Overall_Rating",
            "Difficulty",
            "Would_Take_Again_Pct",
            "Num_Ratings",
            "RMP_ID",
            "RMP_URL",
        ],
    )

    writer.writeheader()

    for teacher in all_teachers:
        node = teacher["node"]

        writer.writerow(
            {
                "Name": f"{node['firstName']} {node['lastName']}",
                "Department": node["department"],
                "Overall_Rating": node["avgRating"],
                "Difficulty": node["avgDifficulty"],
                "Would_Take_Again_Pct": (
                    f"{node['wouldTakeAgainPercent']}%"
                    if node["wouldTakeAgainPercent"] is not None
                    else ""
                ),
                "Num_Ratings": node["numRatings"],
                "RMP_ID": node["legacyId"],
                "RMP_URL": f"https://www.ratemyprofessors.com/professor/{node['legacyId']}",
            }
        )

print(
    f"Done! Saved all {len(all_teachers)} professors to howard_professors_rmp.csv"
)