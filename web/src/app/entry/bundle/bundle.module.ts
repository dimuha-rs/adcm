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
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Routes, RouterModule } from '@angular/router';
import { AuthGuard } from '@app/core';
import { StackComponent, MainComponent } from './stack.component';
import { DetailComponent, SharedModule } from '@app/shared';

const routes: Routes = [
  {
    path: '',
    canActivate: [AuthGuard],
    component: StackComponent,
  },
  {
    path: ':bundle',
    canActivate: [AuthGuard],
    component: DetailComponent,
    children: [{ path: '', redirectTo: 'main', pathMatch: 'full' }, { path: 'main', component: MainComponent }],
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class BundleRoutingModule {}

@NgModule({
  declarations: [StackComponent, MainComponent],
  imports: [CommonModule, SharedModule, BundleRoutingModule, RouterModule, BundleRoutingModule],
})
export class BundleModule {}
