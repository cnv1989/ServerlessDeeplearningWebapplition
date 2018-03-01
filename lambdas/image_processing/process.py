import sys
sys.path.insert(0,'./requirements')


import boto3
import io
import json
import logging
import numpy as np
import os

from PIL import Image
from yolo_utils import *


MODELS = {
    'YOLO': {
        'functionName': 'Yolo',
        'image_size': (608, 608)
    }
}

logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

s3 = boto3.resource('s3')
s3_client = boto3.client('s3')

S3_BUCKET = list(filter(
        lambda output: output.get('OutputKey') == 'ImageStore',
        json.load(open('./StackOutput.json'))["Stacks"][0]["Outputs"]
    ))[0]["OutputValue"]


def preprocess_image(image, model_image_size):
    resized_image = image.resize(tuple(reversed(model_image_size)), Image.BICUBIC)
    image_data = np.array(resized_image, dtype='float32')
    image_data /= 255.
    image_data = np.expand_dims(image_data, 0)  # Add batch dimension.
    return image, image_data


def handler(event, context):
    bucket = s3.Bucket(S3_BUCKET)
    image_name = json.loads(event.get('body'))["image_name"]
    image_obj = bucket.Object(image_name)
    file_stream = io.BytesIO()
    out_image_name = "classified-{}".format(image_name)
    image_output_path = os.path.join(os.sep, 'tmp', out_image_name)
    image_obj.download_fileobj(file_stream)
    pil_image = Image.open(file_stream)
    image, image_data = preprocess_image(pil_image, model_image_size=(608, 608))
    payload = {
        'image_data': image_data.tolist(),
        'image_size': image.size
    }
    s3.Object(S3_BUCKET, 'yolo-{}.json'.format(image_name)).put(
        Body=(bytes(json.dumps(payload, indent=2).encode('UTF-8')))
    )
    return {
        'statusCode': 200,
        'body': json.dumps({
            'image_name': image_name
        })
    }

    # obj_classes = open('./coco_classes.txt', 'r').readlines()
    # obj_classes = list(map(lambda cls: cls.strip(), obj_classes))
    # colors = generate_colors(obj_classes)
    # draw_boxes(image, out_scores, out_boxes, out_classes, obj_classes, colors)

    # out_image.save(image_output_path, quality=90)
    # s3_client.upload_file(image_output_path, S3_BUCKET, out_image_name)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'image_name': image_name,
            'classified_image_name': out_image_name
        })
    }