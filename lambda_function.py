
import logging
import boto3
import json
import requests
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')


def publish_to_sns(course_name: str, lecture: str, section: str, course_id: str):
    sns.publish(
        TopicArn=os.getenv('SNS_TOPIC_ARN'),
        Message=f"I'm gonna need you to hurry because {course_name} {lecture} {section} has opened up!",
        Subject=f"{course_id}: {course_name} {lecture} {section} has opened up!",
    )


def lambda_handler(event, context):
    courses_to_track = event["courses"]

    courses_to_check = []
    for course in courses_to_track:
        semester = course['semester']
        subject = course['subject']
        course_number = course['course_number']
        url = f'https://classes.cornell.edu/api/2.0/search/classes.json?roster={semester}&subject={subject}&q={course_number}'
        response = requests.get(url)
        data = response.json()
        course_id = data['data']['classes'][0]['crseId']
        course_name = f"{data['data']['classes'][0]['subject']} {data['data']['classes'][0]['catalogNbr']}"
        new_sections = data['data']['classes'][0]['enrollGroups']

        # Note to self: Courses are being tracked wholistically, not by section, lecture or DIS
        courses_to_check.append({
            'course_id': course_id,
            'course_name': course_name,
            'sections': new_sections
        })

    table = dynamodb.Table('course')

    for index, course in enumerate(courses_to_check):
        print(f"Checking {course['course_name']}...")
        response = table.get_item(
            Key={
                'course_id': str(course['course_id']),
                'course_name': course['course_name']
            }
        )

        if 'Item' in response:
            old_sections = response['Item']['sections']
            for section_index, section in enumerate(old_sections):
                for k in range(len(section['classSections'])):
                    old_open_status = section['classSections'][k]['openStatus']
                    new_open_status = course['sections'][section_index]['classSections'][k]['openStatus']
                    # check if status has changed from "C" to "O"
                    if (old_open_status == "C" or old_open_status == "W") and new_open_status == "O":
                        lecture_or_discussion = section['classSections'][k]['ssrComponent']
                        actual_section = section['classSections'][k]['section']

                        logger.info(
                            f"{course_name} {lecture_or_discussion} {actual_section} has opened up!")
                        publish_to_sns(course_name, lecture_or_discussion,
                                       actual_section, course['course_id'])
                        # update database
                        table.update_item(
                            Key={
                                'course_id': str(course['course_id']),
                                'course_name': course['course_name']
                            },
                            UpdateExpression="set sections=:s",
                            ExpressionAttributeValues={
                                ':s': course['sections']
                            },
                            ReturnValues="UPDATED_NEW"
                        )
        else:
            table.put_item(
                Item={
                    'course_id': str(course['course_id']),
                    'course_name': course['course_name'],
                    'sections': course['sections']
                }
            )

    return {
        'statusCode': 200,
        'body': json.dumps('That was a breeze!')
    }
