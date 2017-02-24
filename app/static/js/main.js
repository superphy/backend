var app = angular.module('SpfyApp', [])

app.controller('SpfyController', [
    '$scope',
    '$log',
    '$http',
    '$timeout',
    function($scope, $log, $http, $timeout) {

        $scope.loading = false;
        $scope.urlerror = false;

        // for table sort/search
        $scope.sortType     = 'filename'; // set the default sort type
        $scope.sortReverse  = false;  // set the default sort order
        $scope.searchFish   = '';     // set the default search/filter term

        // define form in scope
        $scope.formData={};

        $scope.getResults = function() {

            // get the URL from the input
            var userInput = $scope.myFile;

            // fire the API request
            var fd = new FormData();
            fd.append('file', userInput);
            fd.append('options.vf', $scope.formData.options.vf);
            $log.log(fd);
            $http.post('/upload', fd, {
                transformRequest: angular.identity,
                headers: {
                    'Content-Type': undefined
                }
            }).success(function(results) {
                $log.log(results);
                $scope.spits = [];
                getSpfySpit(results);
                $scope.loading = true;
                $scope.urlerror = false;
                //will have to add this in server resp
                //$scope.message = data.message;
            }).error(function(error) {
                $log.log(error);
            });

        };

        function getSpfySpit(results) {

            var timeout = '';

            var poller = function(key) {
                // fire another request
                if (key !== undefined) {
                    $http.get('/results/' + key).success(function(data, status, headers, config) {
                        if (status === 200) {
                            $log.log(data);
                            $scope.loading = false;
                            $scope.submitButtonText = "Submit";
                            $scope.spits = $scope.spits.concat(data);
                            $log.log($scope.spits)
                            $timeout.cancel(timeout);
                            return false;
                        } else if (status == 202){
                          $scope.loading = true;
                        }
                        // continue to call the poller() function every 2 seconds
                        // until the timeout is cancelled
                        timeout = $timeout(poller(key), 2000);
                    }).error(function(error) {
                        $log.log(error);
                        $scope.loading = false;
                        $scope.submitButtonText = "Submit";
                        $scope.urlerror = true;

                    });
                };

            }

            angular.forEach(results, function(value, key) {
                $log.log(value, key);
                poller(key)
            });

        }

    }
])

app.directive('fileModel', [
    '$parse',
    function($parse) {
        return {
            restrict: 'A',
            link: function(scope, element, attrs) {
                var model = $parse(attrs.fileModel);
                var modelSetter = model.assign;

                element.bind('change', function() {
                    scope.$apply(function() {
                        modelSetter(scope, element[0].files[0]);
                    });
                });
            }
        };
    }
]);

app.directive('exportToCsv', function() {
    return {
        restrict: 'A',
        link: function(scope, element, attrs) {
            var el = element[0];
            element.bind('click', function(e) {
                var table = e.target.nextElementSibling;
                var csvString = '';
                for (var i = 0; i < table.rows.length; i++) {
                    var rowData = table.rows[i].cells;
                    for (var j = 0; j < rowData.length; j++) {
                        csvString = csvString + rowData[j].textContent.trim() + ",";
                    }
                    csvString = csvString.substring(0, csvString.length - 1);
                    csvString = csvString + "\n";
                }
                csvString = csvString.substring(0, csvString.length - 1);
                var a = $('<a/>', {
                    style: 'display:none',
                    href: 'data:application/octet-stream;base64,' + btoa(csvString),
                    download: 'results.csv'
                }).appendTo('body')
                a[0].click()
                a.remove();
            });
        }
    }
});
