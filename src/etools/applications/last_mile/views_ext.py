from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


def generate_csv(data):
    import csv
    import random
    n = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(2))
    with open(f'data_{n}.csv', 'w', newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(data.items())


class VisionIngestApiView(APIView):
    def post(self, request):
        print(request.data)
        generate_csv(request.data)
        return Response({}, status=status.HTTP_200_OK)
