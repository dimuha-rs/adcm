// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { Component, OnInit } from '@angular/core';

import { FieldDirective } from './field.directive';
import { debounceTime } from 'rxjs/operators';

@Component({
  selector: 'app-fields-json',
  template: `
    <ng-container [formGroup]="form">
      <mat-form-field>
        <textarea matInput [appMTextarea]="field.key" [formControlName]="field.name" [readonly]="field.read_only"></textarea>
        <mat-error *ngIf="!isValid"><app-error-info [field]="field" [control]="control"></app-error-info></mat-error>
      </mat-form-field>
    </ng-container>
  `,
})
export class JsonComponent extends FieldDirective implements OnInit {

  ngOnInit(): void {
    super.ngOnInit();
    const control = this.form.controls[this.field.name];
    control.valueChanges.pipe(debounceTime(500)).subscribe((value) => {
      try {
        const v = JSON.parse(value);
        control.setValue(JSON.stringify(v, undefined, 4));
      } catch (e) {}
    });
  }

}
